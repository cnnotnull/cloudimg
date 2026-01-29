from datetime import datetime
from typing import Optional
from app.models.base import Base
from sqlalchemy import JSON, BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import relationship, mapped_column, Mapped


class StorageEngine(Base):
    __tablename__ = "storage_engines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # s3, oss, cos, r2, local
    config: Mapped[dict] = mapped_column(JSON, nullable=False)  # 加密的配置信息
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    path_rule: Mapped[str] = mapped_column(
        String(500), default="uploads/{date}/{filename}.{ext}"
    )
    max_capacity: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )  # 字节单位，None表示无限制
    used_capacity: Mapped[int] = mapped_column(BigInteger, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(),nullable=True
    )

    # 索引
    __table_args__ = (Index("idx_storage_active_default", "is_active", "is_default"),)

    # 关系
    images = relationship("Image", back_populates="storage_engine")
