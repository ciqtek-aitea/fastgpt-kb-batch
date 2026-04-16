"""批量上传编排服务 — 接收前端文件、创建文件夹、并发上传"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.config import DEFAULT_CONCURRENCY, SUPPORTED_EXTS
from app.services import fastgpt_service


def scan_directory(local_dir: str) -> dict:
    """扫描本地目录，返回 dirs 和 files 列表"""
    base = Path(local_dir)
    if not base.is_dir():
        raise FileNotFoundError(f"目录不存在: {local_dir}")

    dirs: list[str] = []
    files: list[str] = []

    for root, dirnames, filenames in os.walk(base):
        rel_root = str(Path(root).relative_to(base))
        for d in sorted(dirnames):
            dirs.append(os.path.join(rel_root, d) if rel_root != "." else d)
        for f in sorted(filenames):
            if Path(f).suffix.lower() in SUPPORTED_EXTS:
                files.append(os.path.join(rel_root, f) if rel_root != "." else f)

    return {"dirs": dirs, "files": files}


def strip_root(path: str) -> str:
    """去掉相对路径的第一层目录名

    webkitRelativePath 格式: "DirName/sub/file.pdf" → "sub/file.pdf"
    """
    parts = Path(path).parts
    if len(parts) <= 1:
        return ""
    return str(Path(*parts[1:]))


async def batch_upload_from_files(
    task_id: str,
    token: str,
    dataset_id: str,
    file_entries: list[tuple[str, bytes]],
    concurrency: int = DEFAULT_CONCURRENCY,
    progress_callback=None,
) -> dict:
    """从前端接收的文件批量上传到 FastGPT

    file_entries: [(stripped_relative_path, file_bytes), ...]
    """
    result = {"uploaded": 0, "failed": []}

    # ---- 提取目录结构 ----
    if progress_callback:
        await progress_callback("scanning", 0, 1, "分析文件结构...")

    dirs: set[str] = set()
    for rel_path, _ in file_entries:
        parent = str(Path(rel_path).parent)
        if parent and parent != ".":
            parts = Path(parent).parts
            for i in range(1, len(parts) + 1):
                dirs.add(str(Path(*parts[:i])))

    dirs_sorted = sorted(dirs, key=lambda d: d.count(os.sep))
    total_files = len(file_entries)

    if progress_callback:
        await progress_callback(
            "scanning", 1, 1,
            f"扫描完成: {len(dirs_sorted)} 个子目录, {total_files} 个文件",
        )

    if not file_entries:
        if progress_callback:
            await progress_callback("done", 0, 0, "没有可上传的文件")
        return result

    # ---- 创建文件夹 ----
    path_to_id: dict[str, str] = {}

    if dirs_sorted:
        if progress_callback:
            await progress_callback("creating_folders", 0, len(dirs_sorted), "创建文件夹...")

        for i, dir_path in enumerate(dirs_sorted):
            parts = Path(dir_path).parts
            parent_collection_id = None
            if len(parts) > 1:
                parent_key = str(Path(*parts[:-1]))
                parent_collection_id = path_to_id.get(parent_key)

            try:
                folder_id = await fastgpt_service.create_folder(
                    token, dataset_id, parts[-1], parent_collection_id,
                )
                path_to_id[dir_path] = folder_id
            except Exception:
                pass

            if progress_callback:
                await progress_callback(
                    "creating_folders", i + 1, len(dirs_sorted),
                    f"已创建文件夹 {i + 1}/{len(dirs_sorted)}",
                )

    # ---- 并发上传文件 ----
    if progress_callback:
        await progress_callback("uploading", 0, total_files, "开始上传文件...")

    semaphore = asyncio.Semaphore(concurrency)
    uploaded_count = 0
    lock = asyncio.Lock()

    async def upload_one(rel_path: str, file_bytes: bytes):
        nonlocal uploaded_count
        async with semaphore:
            parent_dir = str(Path(rel_path).parent)
            collection_parent_id = path_to_id.get(parent_dir) if parent_dir and parent_dir != "." else None
            filename = Path(rel_path).name
            file_size = len(file_bytes)
            last_reported_pct = -1

            async def on_file_progress(sent: int, total: int):
                nonlocal last_reported_pct
                pct = int(sent * 100 / total)
                # 节流：每 5% 上报一次，避免 WebSocket 消息过于频繁
                if pct == last_reported_pct or (pct < 100 and pct % 5 != 0):
                    return
                last_reported_pct = pct

                if progress_callback:
                    # 整体进度 = 已完成文件数 + 当前文件比例
                    async with lock:
                        overall_current = uploaded_count + sent / total
                    await progress_callback(
                        "uploading", overall_current, total_files,
                        f"上传中 {filename} ({pct}%)",
                        file_progress={"name": filename, "sent": sent, "total": total, "percent": pct},
                    )

            try:
                await fastgpt_service.upload_file_via_s3(
                    token=token,
                    file_bytes=file_bytes,
                    filename=filename,
                    dataset_id=dataset_id,
                    parent_id=collection_parent_id,
                    training_type="chunk",
                    chunk_size=512,
                    auto_indexes=True,
                    index_prefix_title=True,
                    image_index=True,
                    file_progress_fn=on_file_progress,
                )
                async with lock:
                    uploaded_count += 1
                    result["uploaded"] = uploaded_count
                if progress_callback:
                    await progress_callback(
                        "uploading", uploaded_count, total_files,
                        f"已上传 {uploaded_count}/{total_files}: {filename}",
                    )
            except Exception as e:
                async with lock:
                    uploaded_count += 1
                    result["failed"].append({"file": filename, "error": str(e)})
                if progress_callback:
                    await progress_callback(
                        "uploading", uploaded_count, total_files,
                        f"上传失败 {filename}: {e}",
                    )

    tasks = [upload_one(path, data) for path, data in file_entries]
    await asyncio.gather(*tasks)

    success_count = result["uploaded"] - len(result["failed"])
    msg = f"上传完成: 成功 {success_count}, 失败 {len(result['failed'])}"
    if progress_callback:
        await progress_callback("done", uploaded_count, total_files, msg)

    return result
