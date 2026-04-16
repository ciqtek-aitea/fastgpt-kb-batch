"""WebSocket 进度管理器 — 管理上传任务的实时进度推送"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import WebSocket


class ProgressManager:
    """管理 WebSocket 连接，支持按 task_id 广播进度"""

    def __init__(self):
        # task_id -> set of WebSocket
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, task_id: str):
        await websocket.accept()
        if task_id not in self._connections:
            self._connections[task_id] = set()
        self._connections[task_id].add(websocket)

    def disconnect(self, websocket: WebSocket, task_id: str):
        if task_id in self._connections:
            self._connections[task_id].discard(websocket)
            if not self._connections[task_id]:
                del self._connections[task_id]

    async def broadcast(self, task_id: str, data: dict[str, Any]):
        """向所有订阅该 task_id 的 WebSocket 发送消息"""
        connections = self._connections.get(task_id, set())
        if not connections:
            return

        message = json.dumps(data, ensure_ascii=False)
        dead: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws, task_id)


# 全局单例
progress_manager = ProgressManager()
