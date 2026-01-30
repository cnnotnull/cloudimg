"""
认证相关的Schema定义
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名", min_length=1, max_length=50)
    password: str = Field(..., description="密码", min_length=1, max_length=100)
    remember_me: bool = Field(default=False, description="是否记住登录")


class LoginResponse(BaseModel):
    """登录响应"""
    username: str = Field(..., description="用户名")
    session_id: str = Field(..., description="会话ID")
    remember_me: bool = Field(..., description="是否记住登录")


class UserInfo(BaseModel):
    """用户信息"""
    username: str = Field(..., description="用户名")
    logged_in: bool = Field(..., description="是否已登录")
