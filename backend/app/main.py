"""FastGPT Web 后端 — FastAPI 应用入口"""

from __future__ import annotations

import socket
import threading
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import auth, collections, datasets, filesystem, upload
from app.ws.progress import progress_manager

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(
    title="FastGPT Web API",
    description="FastGPT 数据集和知识库管理后端",
    version="0.1.0",
    redirect_slashes=False,
)

# CORS — 开发模式允许 Vite dev server 访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由（统一 /api 前缀）
app.include_router(auth.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(collections.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(filesystem.router, prefix="/api")


@app.websocket("/ws/upload/{task_id}")
async def upload_websocket(websocket: WebSocket, task_id: str):
    """WebSocket — 实时推送上传进度"""
    await progress_manager.connect(websocket, task_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        progress_manager.disconnect(websocket, task_id)


# ---- 生产模式：serve 前端静态文件 ----
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback：非 API/WS 的路径返回 index.html"""
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")


def find_free_port() -> int:
    """找一个可用端口"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


if __name__ == "__main__":
    port = find_free_port()
    url = f"http://localhost:{port}"
    print(f"FastGPT 知识库批量上传工具已启动: {url}")
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="warning")
