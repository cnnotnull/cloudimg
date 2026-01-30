"""
认证相关API
"""
from fastapi import APIRouter, Depends, Response, status
from app.schemas.auth import LoginRequest, LoginResponse, UserInfo
from app.schemas.response import BaseResponse, ResponseMessages
from app.config.settings import settings
from app.core.session import session_manager
from app.core.auth import get_current_user, optional_auth


router = APIRouter(tags=["认证"])


@router.post("/auth/login", response_model=BaseResponse)
async def login(
    request: LoginRequest,
    response: Response
):
    """
    用户登录
    
    - **username**: 用户名
    - **password**: 密码
    - **remember_me**: 是否记住登录（可选，默认false）
    """
    # 验证用户名和密码
    if request.username != settings.ADMIN_USERNAME or request.password != settings.ADMIN_PASSWORD:
        return BaseResponse.error_response(
            message="用户名或密码错误"
        )
    
    # 创建session
    session_id = session_manager.create_session(
        username=request.username,
        remember_me=request.remember_me
    )
    
    # 设置cookie
    response.set_cookie(
        key="session_id",
        value=session_id,
        httponly=True,
        secure=not settings.DEBUG,  # 生产环境使用https
        samesite="lax",
        max_age=settings.SESSION_REMEMBER_DAYS * 24 * 60 * 60 if request.remember_me else None
    )
    
    # 返回登录成功信息
    return BaseResponse.success_response(
        message="登录成功",
        data=LoginResponse(
            username=request.username,
            session_id=session_id,
            remember_me=request.remember_me
        )
    )


@router.post("/auth/logout", response_model=BaseResponse)
async def logout(
    response: Response,
    current_user: dict = Depends(get_current_user)
):
    """
    用户登出
    
    需要登录
    """
    # 删除session
    session_manager.delete_session(current_user["session_id"])
    
    # 清除cookie
    response.delete_cookie(key="session_id")
    
    return BaseResponse.success_response(
        message="登出成功"
    )


@router.get("/auth/me", response_model=BaseResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    获取当前登录用户信息
    
    需要登录
    """
    return BaseResponse.success_response(
        message="获取成功",
        data=UserInfo(
            username=current_user["username"],
            logged_in=True
        )
    )


@router.get("/auth/check", response_model=BaseResponse)
async def check_auth(
    current_user: dict = Depends(optional_auth)
):
    """
    检查登录状态
    
    不需要登录，返回当前用户信息或未登录状态
    """
    if current_user:
        return BaseResponse.success_response(
            message="已登录",
            data=UserInfo(
                username=current_user["username"],
                logged_in=True
            )
        )
    else:
        return BaseResponse.success_response(
            message="未登录",
            data=UserInfo(
                username="",
                logged_in=False
            )
        )
