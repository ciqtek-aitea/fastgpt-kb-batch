"""本地文件系统浏览路由"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/fs", tags=["filesystem"])


@router.get("/browse")
async def browse_directory(path: str = Query(default="~")):
    """列出指定目录下的子目录和文件"""
    target = Path(os.path.expanduser(path)).resolve()

    if not target.exists():
        return {"code": 404, "message": f"路径不存在: {target}"}
    if not target.is_dir():
        return {"code": 400, "message": f"不是目录: {target}"}

    try:
        entries = sorted(target.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return {"code": 403, "message": f"无权限访问: {target}"}

    directories = []
    files = []
    for entry in entries:
        # 跳过隐藏文件
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            try:
                child_count = sum(1 for _ in entry.iterdir() if not _.name.startswith("."))
            except PermissionError:
                child_count = 0
            directories.append({
                "name": entry.name,
                "path": str(entry),
                "itemCount": child_count,
            })
        elif entry.is_file():
            stat = entry.stat()
            files.append({
                "name": entry.name,
                "path": str(entry),
                "size": stat.st_size,
            })

    return {
        "code": 200,
        "data": {
            "path": str(target),
            "parent": str(target.parent) if str(target) != "/" else None,
            "directories": directories,
            "files": files,
            "fileCount": len(files),
        },
    }
