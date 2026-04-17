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

    增量上传：上传前查询知识库已有文件，跳过同名同路径的文件。
    """
    result = {"uploaded": 0, "skipped": 0, "failed": [], "failed_entries": []}

    # ---- 查询知识库已有文件和文件夹（增量去重） ----
    if progress_callback:
        await progress_callback("scanning", 0, 1, "查询知识库已有文件...")

    try:
        existing_files, folder_id_map = await fastgpt_service.list_all_file_paths(token, dataset_id)
    except Exception:
        existing_files = set()
        folder_id_map = {}

    # 过滤掉已存在的文件
    filtered_entries = []
    for rel_path, file_bytes in file_entries:
        if rel_path in existing_files:
            result["skipped"] += 1
        else:
            filtered_entries.append((rel_path, file_bytes))

    skipped_count = result["skipped"]
    file_entries = filtered_entries

    if progress_callback:
        await progress_callback(
            "scanning", 1, 1,
            f"已有 {len(existing_files)} 个文件，跳过 {skipped_count} 个，需上传 {len(file_entries)} 个"
            if skipped_count > 0 else
            f"知识库无已有文件，共 {len(file_entries)} 个待上传",
        )

    if not file_entries:
        if progress_callback:
            await progress_callback("done", 0, 0, f"所有文件已存在，跳过 {skipped_count} 个")
        return result

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

    # ---- 创建文件夹（复用已有文件夹） ----
    path_to_id: dict[str, str] = dict(folder_id_map)  # 预填充已有文件夹

    # 只创建不存在的文件夹
    dirs_to_create = [d for d in dirs_sorted if d not in path_to_id]

    if dirs_to_create:
        if progress_callback:
            await progress_callback("creating_folders", 0, len(dirs_to_create), "创建文件夹...")

        for i, dir_path in enumerate(dirs_to_create):
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
                    "creating_folders", i + 1, len(dirs_to_create),
                    f"已创建文件夹 {i + 1}/{len(dirs_to_create)}",
                )
    elif folder_id_map and progress_callback:
        await progress_callback(
            "creating_folders", len(folder_id_map), len(folder_id_map),
            f"复用已有 {len(folder_id_map)} 个文件夹",
        )

    # ---- 并发上传文件 ----
    if progress_callback:
        await progress_callback("uploading", 0, total_files, f"开始上传 0/{total_files}...")

    semaphore = asyncio.Semaphore(concurrency)
    uploaded_count = 0
    success_count = 0
    fail_count = 0
    lock = asyncio.Lock()

    async def upload_one(rel_path: str, file_bytes: bytes):
        nonlocal uploaded_count, success_count, fail_count
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
                    async with lock:
                        overall_current = uploaded_count + sent / total
                    await progress_callback(
                        "uploading", overall_current, total_files,
                        f"上传中 {uploaded_count + 1}/{total_files}: {filename} ({pct}%)",
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
                    success_count += 1
                    result["uploaded"] = success_count
                if progress_callback:
                    await progress_callback(
                        "uploading", uploaded_count, total_files,
                        f"已完成 {uploaded_count}/{total_files}: {filename}",
                    )
            except Exception as e:
                async with lock:
                    uploaded_count += 1
                    fail_count += 1
                    result["failed"].append({"file": rel_path, "error": str(e)})
                    result["failed_entries"].append((rel_path, file_bytes))
                if progress_callback:
                    await progress_callback(
                        "uploading", uploaded_count, total_files,
                        f"已完成 {uploaded_count}/{total_files}: {filename} 失败",
                    )

    tasks = [upload_one(path, data) for path, data in file_entries]
    await asyncio.gather(*tasks)

    failed_list = result["failed"]
    msg = f"上传完成: 成功 {success_count}/{total_files}"
    if fail_count > 0:
        msg += f", 失败 {fail_count}"
    if progress_callback:
        await progress_callback(
            "done", uploaded_count, total_files, msg,
            failed_files=failed_list if failed_list else None,
        )

    return result
