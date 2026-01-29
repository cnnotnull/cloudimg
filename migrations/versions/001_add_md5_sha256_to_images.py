"""Add MD5 and SHA256 to images table, change ID to autoincrement

Revision ID: 001
Revises: 
Create Date: 2026-01-29 16:21:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Upgrade to add MD5 and SHA256 columns and fix ID autoincrement."""
    
    # SQLite不支持直接修改主键，需要重建表
    op.execute("""
        CREATE TABLE images_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            md5 VARCHAR(32) NOT NULL,
            sha256 VARCHAR(64) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,
            storage_filename VARCHAR(500) NOT NULL,
            storage_engine_id INTEGER NOT NULL,
            file_size BIGINT NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            width INTEGER,
            height INTEGER,
            upload_ip VARCHAR(45),
            extra_metadata JSON,
            original_url TEXT NOT NULL,
            thumbnail_url TEXT,
            is_deleted BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(storage_engine_id) REFERENCES storage_engines(id)
        )
    """)
    
    # 复制数据（注意：旧的MD5 ID现在存储到md5字段）
    op.execute("""
        INSERT INTO images_new (
            md5, sha256, original_filename, storage_filename,
            storage_engine_id, file_size, file_type, width, height,
            upload_ip, extra_metadata, original_url, thumbnail_url,
            is_deleted, created_at
        )
        SELECT 
            id, id, original_filename, storage_filename,
            storage_engine_id, file_size, file_type, width, height,
            upload_ip, extra_metadata, original_url, thumbnail_url,
            is_deleted, created_at
        FROM images
    """)
    
    # 删除旧表
    op.execute("DROP TABLE images")
    
    # 重命名新表
    op.execute("ALTER TABLE images_new RENAME TO images")
    
    # 创建索引
    op.execute("CREATE INDEX ix_images_id ON images (id)")
    op.execute("CREATE INDEX ix_images_md5 ON images (md5)")
    op.execute("CREATE INDEX ix_images_sha256 ON images (sha256)")
    op.execute("CREATE INDEX ix_images_storage_engine_id ON images (storage_engine_id)")
    op.execute("CREATE INDEX ix_images_file_type ON images (file_type)")
    op.execute("CREATE INDEX ix_images_is_deleted ON images (is_deleted)")
    op.execute("CREATE INDEX ix_images_created_at ON images (created_at)")


def downgrade():
    """Downgrade to revert MD5/SHA256 changes."""
    
    # 重建旧版本的表
    op.execute("""
        CREATE TABLE images_old (
            id VARCHAR(32) PRIMARY KEY,
            original_filename VARCHAR(255) NOT NULL,
            storage_filename VARCHAR(500) NOT NULL,
            storage_engine_id INTEGER NOT NULL,
            file_size BIGINT NOT NULL,
            file_type VARCHAR(50) NOT NULL,
            width INTEGER,
            height INTEGER,
            upload_ip VARCHAR(45),
            extra_metadata JSON,
            original_url TEXT NOT NULL,
            thumbnail_url TEXT,
            is_deleted BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(storage_engine_id) REFERENCES storage_engines(id)
        )
    """)
    
    # 复制数据（使用md5作为新的id）
    op.execute("""
        INSERT INTO images_old (
            id, original_filename, storage_filename,
            storage_engine_id, file_size, file_type, width, height,
            upload_ip, extra_metadata, original_url, thumbnail_url,
            is_deleted, created_at
        )
        SELECT 
            md5, original_filename, storage_filename,
            storage_engine_id, file_size, file_type, width, height,
            upload_ip, extra_metadata, original_url, thumbnail_url,
            is_deleted, created_at
        FROM images
    """)
    
    # 删除新表
    op.execute("DROP TABLE images")
    
    # 重命名回旧表
    op.execute("ALTER TABLE images_old RENAME TO images")
    
    # 重建索引
    op.execute("CREATE INDEX ix_images_id ON images (id)")
    op.execute("CREATE INDEX ix_images_storage_engine_id ON images (storage_engine_id)")
    op.execute("CREATE INDEX ix_images_file_type ON images (file_type)")
    op.execute("CREATE INDEX ix_images_is_deleted ON images (is_deleted)")
    op.execute("CREATE INDEX ix_images_created_at ON images (created_at)")
