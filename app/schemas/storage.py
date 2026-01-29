from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class StorageEngineBase(BaseModel):
    """存储引擎基础模型"""
    name: str = Field(..., description="存储引擎名称", max_length=100)
    type: str = Field(..., description="存储类型", pattern="^(local|s3|oss|cos|r2)$")
    config: dict = Field(..., description="存储配置（加密存储）")
    path_rule: str = Field(
        default="uploads/{date}/{filename}.{ext}",
        description="路径规则",
        max_length=500
    )
    max_capacity: Optional[int] = Field(None, description="最大容量（字节），None表示无限制")
    is_active: bool = Field(default=True, description="是否激活")


class StorageEngineCreate(StorageEngineBase):
    """创建存储引擎请求"""
    pass


class StorageEngineUpdate(BaseModel):
    """更新存储引擎请求（只允许修改名称、状态和容量）"""
    name: Optional[str] = Field(None, description="存储引擎名称", max_length=100)
    is_active: Optional[bool] = Field(None, description="是否激活")
    max_capacity: Optional[int] = Field(None, description="最大容量（字节），必须大于已使用容量", ge=0)


class StorageEngineResponse(StorageEngineBase):
    """存储引擎响应"""
    id: int
    is_default: bool
    used_capacity: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class StorageEngineUsage(BaseModel):
    """存储使用情况"""
    used_capacity: int = Field(..., description="已使用容量（字节）")
    max_capacity: Optional[int] = Field(None, description="最大容量（字节）")
    usage_percent: Optional[float] = Field(None, description="使用百分比")
    file_count: Optional[int] = Field(None, description="文件数量")
    available: bool = Field(..., description="是否可用")


class StorageEngineTestResult(BaseModel):
    """存储连接测试结果"""
    success: bool = Field(..., description="测试是否成功")
    message: str = Field(..., description="测试消息")
    latency: Optional[float] = Field(None, description="延迟（毫秒）")
