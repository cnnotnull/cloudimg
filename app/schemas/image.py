from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ImageBase(BaseModel):
    """图片基础模型"""
    original_filename: str = Field(..., description="原始文件名", max_length=255)
    file_type: str = Field(..., description="文件类型", max_length=50)
    file_size: int = Field(..., description="文件大小（字节）", gt=0)
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")
    extra_metadata: dict = Field(default_factory=dict, description="扩展元数据")
    md5: str = Field(..., description="MD5哈希值", max_length=32)
    sha256: str = Field(..., description="SHA256哈希值", max_length=64)


class ImageResponse(ImageBase):
    """图片响应"""
    id: int = Field(..., description="图片ID")
    storage_filename: str = Field(..., description="存储文件名")
    storage_engine_id: int = Field(..., description="存储引擎ID")
    original_url: str = Field(..., description="原始图片URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    is_deleted: bool = Field(..., description="是否已删除")
    created_at: datetime = Field(..., description="创建时间")
    
    class Config:
        from_attributes = True


class ImageUploadResponse(BaseModel):
    """图片上传响应"""
    id: int = Field(..., description="图片ID")
    md5: str = Field(..., description="MD5哈希值", max_length=32)
    sha256: str = Field(..., description="SHA256哈希值", max_length=64)
    filename: str = Field(..., description="文件名")
    url: str = Field(..., description="图片URL")
    thumbnail_url: Optional[str] = Field(None, description="缩略图URL")
    size: int = Field(..., description="文件大小")
    width: Optional[int] = Field(None, description="图片宽度")
    height: Optional[int] = Field(None, description="图片高度")


class ImageListQuery(BaseModel):
    """图片列表查询参数"""
    skip: int = Field(0, ge=0, description="跳过数量")
    limit: int = Field(20, ge=1, le=100, description="返回数量")
    storage_engine_id: Optional[int] = Field(None, description="存储引擎ID")
    file_type: Optional[str] = Field(None, description="文件类型")
    is_deleted: Optional[bool] = Field(None, description="是否已删除")
    start_date: Optional[datetime] = Field(None, description="开始日期")
    end_date: Optional[datetime] = Field(None, description="结束日期")
