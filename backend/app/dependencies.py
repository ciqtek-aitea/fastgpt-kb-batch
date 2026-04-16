"""FastAPI 依赖注入 — session token 管理（持久化到文件）"""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from fastapi import Header, HTTPException

_SESSIONS_FILE = Path(__file__).resolve().parent.parent / "sessions.json"

# session_id -> fastgpt_token 映射
sessions: dict[str, str] = {}


def _load_sessions() -> None:
    """从文件加载 sessions"""
    if _SESSIONS_FILE.exists():
        try:
            sessions.update(json.loads(_SESSIONS_FILE.read_text("utf-8")))
        except (json.JSONDecodeError, OSError):
            pass


def _save_sessions() -> None:
    """持久化 sessions 到文件"""
    _SESSIONS_FILE.write_text(json.dumps(sessions, ensure_ascii=False), "utf-8")


def create_session(fastgpt_token: str) -> str:
    """创建新 session，返回 session_id"""
    # 如果已有同一 fastgpt_token 的 session，复用它
    for sid, tok in sessions.items():
        if tok == fastgpt_token:
            return sid

    session_id = secrets.token_urlsafe(32)
    sessions[session_id] = fastgpt_token
    _save_sessions()
    return session_id


async def get_current_token(authorization: str = Header(...)) -> str:
    """从请求头提取 session_token，返回对应的 fastgpt_token

    使用方式: Authorization: Bearer <session_id>
    """
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=401, detail="无效的 Authorization header")

    fastgpt_token = sessions.get(token)
    if not fastgpt_token:
        raise HTTPException(status_code=401, detail="session 已过期或无效，请重新登录")

    return fastgpt_token


def cleanup_session(session_id: str) -> None:
    """删除指定 session"""
    sessions.pop(session_id, None)
    _save_sessions()


# 启动时加载
_load_sessions()
