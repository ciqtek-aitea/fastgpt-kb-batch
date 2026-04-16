"""认证相关 Pydantic 模型"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str  # 明文密码，服务端会做 sha256


class TokenSetRequest(BaseModel):
    token: str


class AuthResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: Optional[str] = None
