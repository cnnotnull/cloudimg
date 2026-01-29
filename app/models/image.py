from datetime import datetime
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import mapped_column, relationship, Mapped

from app.models.base import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, index=True
    )
    md5: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_engine_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("storage_engines.id"), nullable=False, index=True
    )
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    width: Mapped[int] = mapped_column(Integer, nullable=True)
    height: Mapped[int] = mapped_column(Integer, nullable=True)
    upload_ip: Mapped[str] = mapped_column(String(45), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, default=dict)  # 扩展元数据
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_url: Mapped[str] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # 关系
    storage_engine = relationship("StorageEngine", back_populates="images")
