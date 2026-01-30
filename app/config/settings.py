from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "Web图床系统"
    APP_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./db/database.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    
    # 文件上传配置
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    UPLOAD_DIR: str = "./uploads"
    
    # 缩略图配置
    THUMBNAIL_WIDTH: int = 300  # 缩略图宽度
    THUMBNAIL_HEIGHT: int = 300  # 缩略图高度
    THUMBNAIL_SAVE_PATH: str = "./thumbnails"  # 缩略图本地保存路径
    THUMBNAIL_URL_PREFIX: str = "http://localhost:8000"  # 缩略图URL前缀
    
    # 安全配置
    SECRET_KEY: str = "EDcOlV9UZD5KNl2Y0dzA9wBZ2YZvxUzH"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
