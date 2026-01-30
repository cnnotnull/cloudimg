from logging.config import fileConfig
import sys
import os
from urllib.parse import unquote

from sqlalchemy import pool
from sqlalchemy import create_engine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata

# 添加项目根目录到sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入模型元数据
from app.models.base import Base

# 设置target_metadata
target_metadata = Base.metadata

# 从settings获取数据库URL
from app.config.settings import settings


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # 使用同步引擎运行迁移
    database_url = settings.DATABASE_URL
    
    # 将异步URL转换为同步URL
    if "sqlite+aiosqlite" in database_url:
        sync_url = database_url.replace("sqlite+aiosqlite://", "sqlite://")
        
        # 确保SQLite数据库文件的父文件夹存在
        db_path = sync_url.replace("sqlite:///", "")
        # 解码URL编码
        db_path = unquote(db_path)
        # 确保路径是绝对路径
        db_path = os.path.abspath(db_path)
        # 创建父文件夹
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
            print(f"[Alembic] 数据库目录已创建: {db_dir}")
            
    elif "mysql+aiomysql" in database_url:
        sync_url = database_url.replace("mysql+aiomysql://", "mysql+pymysql://")
    elif "postgresql+asyncpg" in database_url:
        sync_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    else:
        sync_url = database_url
    
    # 创建同步引擎
    engine = create_engine(
        sync_url,
        poolclass=pool.NullPool,
    )

    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            render_as_batch=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
