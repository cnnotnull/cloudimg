from contextlib import asynccontextmanager
import hashlib
from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config.settings import settings
from app.config.database import init_db, engine
from app.api import storage_router, image_router, config_router
from app.core.exceptions import AppException, ERROR_CODES
from app.schemas.response import BaseResponse, ResponseMessages
from app.core.storage_cache import storage_cache
from app.core.config_cache import config_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("=" * 50)
    print(f"[START] {settings.APP_NAME} v{settings.APP_VERSION} 正在启动...")
    print(f"[INFO]  API地址: http://{settings.HOST}:{settings.PORT}")
    print(f"[INFO]  API文档: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 50)

    # 初始化数据库（开发环境）
    if settings.DEBUG:
        await init_db()
        print("[OK]    数据库初始化完成")

    # 初始化系统配置
    from app.config.database import get_db
    from app.services.config import ConfigService
    async for db in get_db():
        # 初始化默认配置
        count = await ConfigService.initialize_defaults(db)
        if count > 0:
            print(f"[OK]    初始化了 {count} 条默认配置")
        
        # 加载配置到缓存
        configs = await ConfigService.get_all(db)
        await config_cache.initialize(configs)
        print("[OK]    系统配置缓存初始化完成")
        
        # 初始化存储引擎缓存
        await storage_cache.initialize(db)
        print("[OK]    存储引擎缓存初始化完成")
        break

    yield

    # 关闭时执行
    print("=" * 50)
    print("[STOP]  正在关闭应用...")
    # 清空存储引擎缓存
    storage_cache.clear()
    print("[OK]    存储引擎缓存已清空")
    # 关闭数据库连接
    await engine.dispose()
    print("[OK]    数据库连接已关闭")
    print("[BYE]   应用已安全关闭")
    print("=" * 50)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Web图床系统API",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ==================== 中间件配置 ====================

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """请求日志中间件"""
    import time

    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # 打印请求日志
    print(
        f"[REQ]   {request.method} {request.url.path} "
        f"- 状态码: {response.status_code} "
        f"- 耗时: {process_time:.3f}s"
    )

    # 添加响应头
    response.headers["X-Process-Time"] = str(process_time)
    return response


# ==================== 异常处理 ====================


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """自定义应用异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.detail,
            "data": None,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """数据库异常处理"""
    print(f"[ERROR] 数据库错误: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "DATABASE_ERROR",
            "message": "操作失败",
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    print(f"[ERROR] 未捕获的异常: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_ERROR",
            "message": "服务器内部错误" if not settings.DEBUG else str(exc),
            "data": None,
        },
    )


# ==================== 路由注册 ====================

# 注册API路由
app.include_router(storage_router, prefix=settings.API_V1_STR)
app.include_router(image_router, prefix=settings.API_V1_STR)
app.include_router(config_router, prefix=settings.API_V1_STR)

# 挂载本地图片上传根路径和缩略图目录
import os

upload_dir = settings.UPLOAD_DIR
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# 挂载缩略图目录（注意：这里仍然使用settings中的值作为默认值，
# 实际路径可以通过配置API动态修改，需要重启服务生效）
thumbnail_dir = settings.THUMBNAIL_SAVE_PATH
if not os.path.exists(thumbnail_dir):
    os.makedirs(thumbnail_dir, exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=thumbnail_dir), name="thumbnails")


# ==================== 基础端点 ====================

@app.get("/", tags=["基础"])
async def read_root():
    """根路径 - API 信息"""
    return BaseResponse.success_response(
        message=f"欢迎使用 {settings.APP_NAME}",
        data={
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "docs": "/docs",
            "api_prefix": settings.API_V1_STR,
        },
    )


@app.get("/health", tags=["基础"])
async def health_check():
    """健康检查端点"""
    return BaseResponse.success_response(
        message=ResponseMessages.SYSTEM_HEALTHY,
        data={"status": "healthy", "version": settings.APP_VERSION},
    )


@app.get("/error-codes", tags=["基础"])
async def get_error_codes():
    """获取所有错误码定义（调试用）"""
    if not settings.DEBUG:
        return BaseResponse.error_response(message="仅在调试模式下可用")
    return BaseResponse.success_response(data=ERROR_CODES)


@app.get("/cache/info", tags=["基础"])
async def get_cache_info():
    """获取存储引擎缓存信息（调试用）"""
    if not settings.DEBUG:
        return BaseResponse.error_response(message="仅在调试模式下可用")
    cache_info = storage_cache.get_cache_info()
    return BaseResponse.success_response(data=cache_info)
