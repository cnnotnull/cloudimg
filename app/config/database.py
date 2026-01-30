from typing import AsyncGenerator
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from app.config.settings import settings
from app.models.base import Base


def create_database_engine():
    """创建异步数据库引擎，支持多数据库"""
    database_url = settings.DATABASE_URL
    
    # SQLite配置
    if database_url.startswith("sqlite"):
        # 对于SQLite，需要特殊处理
        if "+aiosqlite" not in database_url:
            database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
        
        # 确保数据库文件的父文件夹存在
        # 从URL中提取文件路径
        db_path = database_url.replace("sqlite+aiosqlite:///", "")
        # 解码URL编码
        from urllib.parse import unquote
        db_path = unquote(db_path)
        # 确保路径是绝对路径
        db_path = os.path.abspath(db_path)
        # 创建父文件夹
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            print(f"[DB]    数据库目录已创建: {db_dir}")
        
        connect_args = {"check_same_thread": False}
        # SQLite 使用 NullPool 或 StaticPool（单线程应用）
        return create_async_engine(
            database_url,
            connect_args=connect_args,
            poolclass=NullPool,  # SQLite 不支持真正的连接池
            echo=settings.DEBUG
        )
    
    # MySQL配置
    elif database_url.startswith("mysql"):
        # 确保使用异步驱动
        if "+aiomysql" not in database_url and "+asyncmy" not in database_url:
            database_url = database_url.replace("mysql://", "mysql+aiomysql://")
        # 添加连接池和字符集配置
        if "?" not in database_url:
            database_url += "?charset=utf8mb4"
        elif "charset=" not in database_url:
            database_url += "&charset=utf8mb4"
        
        # 异步引擎默认使用正确的连接池，只需指定参数
        return create_async_engine(
            database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,  # 连接前ping检测
            echo=settings.DEBUG
        )
    
    # PostgreSQL配置
    elif database_url.startswith("postgresql"):
        # 确保使用异步驱动
        if "+asyncpg" not in database_url:
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
        
        # 异步引擎默认使用正确的连接池，只需指定参数
        return create_async_engine(
            database_url,
            pool_size=settings.DATABASE_POOL_SIZE,
            max_overflow=settings.DATABASE_MAX_OVERFLOW,
            pool_pre_ping=True,
            echo=settings.DEBUG
        )
    
    else:
        raise ValueError(f"不支持的数据库类型: {database_url}")


# 创建异步数据库引擎（用于应用）
engine = create_database_engine()

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
