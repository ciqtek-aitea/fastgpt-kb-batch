"""FastGPT Web 后端 — FastAPI 应用入口"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, collections, datasets, filesystem, upload
from app.ws.progress import progress_manager

app = FastAPI(
    title="FastGPT Web API",
    description="FastGPT 数据集和知识库管理后端",
    version="0.1.0",
    redirect_slashes=False,
)

# CORS — 允许前端开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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


@app.get("/")
async def root():
    return {"message": "FastGPT Web API is running"}


@app.websocket("/ws/upload/{task_id}")
async def upload_websocket(websocket: WebSocket, task_id: str):
    """WebSocket — 实时推送上传进度（顶层路径，匹配 Vite 代理）"""
    await progress_manager.connect(websocket, task_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        progress_manager.disconnect(websocket, task_id)
