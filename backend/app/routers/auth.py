"""认证路由"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.dependencies import create_session, get_current_token
from app.models.auth import AuthResponse, LoginRequest, TokenSetRequest
from app.services import fastgpt_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """账号密码登录"""
    try:
        fastgpt_token = await fastgpt_service.login_password(req.username, req.password)
        session_id = create_session(fastgpt_token)
        return AuthResponse(success=True, token=session_id, message="登录成功")
    except Exception as e:
        return AuthResponse(success=False, message=f"登录失败: {e}")


@router.post("/token", response_model=AuthResponse)
async def set_token(req: TokenSetRequest):
    """手动设置 fastgpt token"""
    valid = await fastgpt_service.validate_token(req.token)
    if not valid:
        return AuthResponse(success=False, message="token 无效")
    session_id = create_session(req.token)
    return AuthResponse(success=True, token=session_id, message="token 验证成功")


@router.get("/check")
async def check_auth(fastgpt_token: str = Depends(get_current_token)):
    """检查当前 session 是否有效"""
    valid = await fastgpt_service.validate_token(fastgpt_token)
    if valid:
        return {"valid": True}
    return {"valid": False}
