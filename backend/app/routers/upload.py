"""批量上传路由"""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import DEFAULT_CONCURRENCY, SUPPORTED_EXTS
from app.dependencies import get_current_token
from app.services import upload_service
from app.ws.progress import progress_manager

logger = logging.getLogger("upload")

router = APIRouter(prefix="/upload", tags=["upload"])

_tasks: dict[str, asyncio.Task] = {}
_task_status: dict[str, dict] = {}  # task_id -> 最后一次进度快照
_task_dataset: dict[str, str] = {}  # task_id -> dataset_id
_task_failed: dict[str, list[tuple[str, bytes]]] = {}  # task_id -> 失败文件条目（用于重试）


class UploadRequest(BaseModel):
    datasetId: str
    directories: list[str] = []
    files: list[str] = []
    concurrency: int = DEFAULT_CONCURRENCY


class RetryRequest(BaseModel):
    taskId: str


@router.post("/preview")
async def preview_upload(req: UploadRequest, token: str = Depends(get_current_token)):
    """预览选中目录和文件的文件"""
    total_files = 0
    total_size = 0
    preview_files = []

    for d in req.directories:
        base = Path(d)
        if not base.is_dir():
            continue
        for root, _, filenames in os.walk(base):
            for f in filenames:
                fp = Path(root) / f
                if fp.suffix.lower() in SUPPORTED_EXTS:
                    total_files += 1
                    total_size += fp.stat().st_size
                    if len(preview_files) < 50:
                        preview_files.append({"name": str(fp.relative_to(base)), "size": fp.stat().st_size})

    for f in req.files:
        fp = Path(f)
        if fp.is_file() and fp.suffix.lower() in SUPPORTED_EXTS:
            total_files += 1
            total_size += fp.stat().st_size
            if len(preview_files) < 50:
                preview_files.append({"name": fp.name, "size": fp.stat().st_size})

    return {"code": 200, "data": {"totalFiles": total_files, "totalSize": total_size, "files": preview_files}}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str, token: str = Depends(get_current_token)):
    """查询上传任务状态"""
    status = _task_status.get(task_id)
    if not status:
        return {"code": 404, "message": "任务不存在"}
    return {"code": 200, "data": status}


@router.get("/tasks")
async def list_tasks(token: str = Depends(get_current_token)):
    """列出所有上传任务"""
    tasks = []
    for task_id, status in _task_status.items():
        tasks.append({
            "taskId": task_id,
            "datasetId": _task_dataset.get(task_id, ""),
            **status,
        })
    # 按创建时间倒序（没有时间戳，用列表原始顺序的逆序）
    tasks.reverse()
    return {"code": 200, "data": tasks}


@router.post("/start")
async def start_upload(req: UploadRequest, token: str = Depends(get_current_token)):
    """启动批量上传"""
    task_id = secrets.token_urlsafe(16)
    _task_dataset[task_id] = req.datasetId

    async def _run():
        await asyncio.sleep(1)  # 等待 WebSocket 连接

        async def on_progress(phase, current, total, message, file_progress=None, failed_files=None):
            data = {
                "taskId": task_id,
                "phase": phase,
                "current": current,
                "total": total,
                "message": message,
            }
            if file_progress:
                data["fileProgress"] = file_progress
            if failed_files:
                data["failedFiles"] = failed_files
            _task_status[task_id] = data
            await progress_manager.broadcast(task_id, data)

        try:
            all_files: list[tuple[str, bytes]] = []

            for dir_path in req.directories:
                dir_name = Path(dir_path).name
                scan = upload_service.scan_directory(dir_path)
                for rel_file in scan["files"]:
                    full = os.path.join(dir_path, rel_file)
                    with open(full, "rb") as f:
                        all_files.append((f"{dir_name}/{rel_file}", f.read()))

            for file_path in req.files:
                fp = Path(file_path)
                with open(file_path, "rb") as f:
                    all_files.append((fp.name, f.read()))

            result = await upload_service.batch_upload_from_files(
                task_id=task_id,
                token=token,
                dataset_id=req.datasetId,
                file_entries=all_files,
                concurrency=req.concurrency,
                progress_callback=on_progress,
            )

            # 保存失败文件条目用于重试
            if result.get("failed_entries"):
                _task_failed[task_id] = result["failed_entries"]

        except Exception as e:
            logger.error(f"Upload task {task_id} failed: {e}", exc_info=True)
            await on_progress("done", 0, 0, f"上传失败: {e}")

    task = asyncio.create_task(_run())
    _tasks[task_id] = task

    return {"code": 200, "data": {"taskId": task_id}, "message": "上传任务已启动"}


@router.post("/retry")
async def retry_failed(req: RetryRequest, token: str = Depends(get_current_token)):
    """重试失败文件"""
    old_task_id = req.taskId
    failed_entries = _task_failed.pop(old_task_id, None)
    dataset_id = _task_dataset.get(old_task_id)

    if not failed_entries:
        return {"code": 400, "message": "没有可重试的文件"}
    if not dataset_id:
        return {"code": 400, "message": "原始任务不存在"}

    task_id = secrets.token_urlsafe(16)
    _task_dataset[task_id] = dataset_id

    async def _run():
        await asyncio.sleep(1)

        async def on_progress(phase, current, total, message, file_progress=None, failed_files=None):
            data = {
                "taskId": task_id,
                "phase": phase,
                "current": current,
                "total": total,
                "message": message,
            }
            if file_progress:
                data["fileProgress"] = file_progress
            if failed_files:
                data["failedFiles"] = failed_files
            _task_status[task_id] = data
            await progress_manager.broadcast(task_id, data)

        try:
            result = await upload_service.batch_upload_from_files(
                task_id=task_id,
                token=token,
                dataset_id=dataset_id,
                file_entries=failed_entries,
                concurrency=DEFAULT_CONCURRENCY,
                progress_callback=on_progress,
            )
            if result.get("failed_entries"):
                _task_failed[task_id] = result["failed_entries"]
        except Exception as e:
            logger.error(f"Retry task {task_id} failed: {e}", exc_info=True)
            await on_progress("done", 0, 0, f"重试失败: {e}")

    task = asyncio.create_task(_run())
    _tasks[task_id] = task

    return {"code": 200, "data": {"taskId": task_id}, "message": "重试任务已启动"}
