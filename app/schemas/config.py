"""
系统配置相关的Schema
"""
from typing import Optional
from pydantic import BaseModel, Field


class SystemConfigBase(BaseModel):
    """系统配置基础模型"""
    key: str = Field(..., description="配置键", max_length=100)
    value: str = Field(..., description="配置值", max_length=500)


class SystemConfigUpdate(BaseModel):
    """更新系统配置请求"""
    value: str = Field(..., description="配置值", max_length=500)


class SystemConfigResponse(SystemConfigBase):
    """系统配置响应"""
    id: int
    
    class Config:
        from_attributes = True


class SystemConfigBatchUpdate(BaseModel):
    """批量更新系统配置请求"""
    configs: dict = Field(..., description="配置字典 {key: value}")


class SystemSettings(BaseModel):
    """系统设置（用于前端展示和编辑）"""
    # 文件上传配置
    max_upload_size: int = Field(default=10 * 1024 * 1024, description="最大上传大小（字节）")
    allowed_image_types: str = Field(default="image/jpeg,image/png,image/gif,image/webp", description="允许的图片类型")
    
    # 缩略图配置
    thumbnail_width: int = Field(default=300, description="缩略图宽度")
    thumbnail_height: int = Field(default=300, description="缩略图高度")
    
    # 系统配置
    system_domain: str = Field(default="http://localhost:8000", description="系统访问域名")
