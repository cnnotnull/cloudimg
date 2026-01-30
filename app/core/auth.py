"""
认证依赖模块
提供FastAPI的认证依赖注入
"""
from typing import Optional
from fastapi import HTTPException, status, Depends, Cookie, Request
from app.config.settings import settings
from app.core.session import session_manager
from app.core.exceptions import AppException, ERROR_CODES


async def get_current_user(
    request: Request,
    session_id: Optional[str] = Cookie(None, alias="session_id")
) -> dict:
    """
    获取当前登录用户
    
    Args:
        request: FastAPI请求对象
        session_id: 从cookie中获取的session_id
        
    Returns:
        当前用户信息
        
    Raises:
        AppException: 未登录或session无效
    """
    if not session_id:
        # 尝试从header中获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header.replace("Bearer ", "")
    
    if not session_id:
        raise AppException(
            error_code=ERROR_CODES["UNAUTHORIZED"],
            detail="未登录，请先登录",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    # 获取session
    session = session_manager.get_session(session_id)
    
    if not session:
        raise AppException(
            error_code=ERROR_CODES["UNAUTHORIZED"],
            detail="登录已过期，请重新登录",
            status_code=status.HTTP_401_UNAUTHORIZED
        )
    
    return {
        "username": session["username"],
        "session_id": session_id,
        "remember_me": session["remember_me"]
    }


async def optional_auth(
    request: Request,
    session_id: Optional[str] = Cookie(None, alias="session_id")
) -> Optional[dict]:
    """
    可选的认证依赖
    如果已登录返回用户信息，否则返回None
    
    Args:
        request: FastAPI请求对象
        session_id: 从cookie中获取的session_id
        
    Returns:
        当前用户信息，未登录则返回None
    """
    if not session_id:
        # 尝试从header中获取
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            session_id = auth_header.replace("Bearer ", "")
    
    if not session_id:
        return None
    
    # 获取session
    session = session_manager.get_session(session_id)
    
    if not session:
        return None
    
    return {
        "username": session["username"],
        "session_id": session_id,
        "remember_me": session["remember_me"]
    }


def require_auth():
    """
    需要认证的依赖
    如果未登录则抛出异常
    
    Returns:
        用户信息
    """
    return Depends(get_current_user)
