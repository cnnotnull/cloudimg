from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.services.storage import StorageService
from app.schemas.storage import (
    StorageEngineCreate,
    StorageEngineUpdate,
    StorageEngineResponse,
    StorageEngineUsage,
    StorageEngineTestResult
)
from app.schemas.response import BaseResponse, ResponseMessages
from app.core.exceptions import AppException, ERROR_CODES
from app.core.storage_cache import storage_cache

router = APIRouter(prefix="/storage/engines", tags=["存储引擎"])


@router.get("", response_model=BaseResponse)
async def get_storage_engines(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(100, ge=1, le=1000, description="返回数量"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_db)
):
    """获取存储引擎列表"""
    storages = await StorageService.get_all(db, skip=skip, limit=limit, is_active=is_active)
    return BaseResponse.success_response(
        data=[StorageEngineResponse.model_validate(s) for s in storages]
    )


@router.post("", response_model=BaseResponse, status_code=201)
async def create_storage_engine(
    storage_data: StorageEngineCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建存储引擎"""
    try:
        storage = await StorageService.create(db, storage_data.model_dump())
        return BaseResponse.created_response(
            data=StorageEngineResponse.model_validate(storage)
        )
    except Exception as e:
        raise AppException(
            status_code=400,
            detail=f"创建失败: {str(e)}",
            error_code="STORAGE_CREATE_FAILED"
        )


@router.get("/{storage_id}", response_model=BaseResponse)
async def get_storage_engine(
    storage_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取存储引擎详情"""
    storage = await StorageService.get_by_id(db, storage_id)
    if not storage:
        raise AppException(
            status_code=404,
            detail="存储引擎不存在",
            error_code=ERROR_CODES["STORAGE_NOT_FOUND"]
        )
    
    return BaseResponse.success_response(
        data=StorageEngineResponse.model_validate(storage)
    )


@router.put("/{storage_id}", response_model=BaseResponse)
async def update_storage_engine(
    storage_id: int,
    storage_data: StorageEngineUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新存储引擎"""
    update_data = storage_data.model_dump(exclude_unset=True)
    storage = await StorageService.update(db, storage_id, update_data)
    
    if not storage:
        raise AppException(
            status_code=404,
            detail="存储引擎不存在",
            error_code=ERROR_CODES["STORAGE_NOT_FOUND"]
        )
    
    return BaseResponse.updated_response(
        data=StorageEngineResponse.model_validate(storage)
    )


@router.delete("/{storage_id}", response_model=BaseResponse)
async def delete_storage_engine(
    storage_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除存储引擎"""
    try:
        success = await StorageService.delete(db, storage_id)
        if not success:
            raise AppException(
                status_code=404,
                detail="存储引擎不存在",
                error_code=ERROR_CODES["STORAGE_NOT_FOUND"]
            )
        
        return BaseResponse.deleted_response()
    except AppException:
        raise
    except Exception as e:
        raise AppException(
            status_code=400,
            detail=f"删除失败: {str(e)}",
            error_code="STORAGE_DELETE_FAILED"
        )


@router.post("/{storage_id}/test", response_model=BaseResponse)
async def test_storage_engine(
    storage_id: int,
    db: AsyncSession = Depends(get_db)
):
    """测试存储引擎连接"""
    # 从缓存获取存储实例
    storage_instance = storage_cache.get_storage(storage_id)
    if not storage_instance:
        # 如果缓存中没有，使用service方法
        result = await StorageService.test_connection(db, storage_id)
        return BaseResponse.success_response(
            message=result["message"],
            data=StorageEngineTestResult(**result)
        )
    
    # 使用缓存的实例测试连接
    try:
        import time
        start_time = time.time()
        success = await storage_instance.test_connection()
        latency = (time.time() - start_time) * 1000  # 转换为毫秒
        
        return BaseResponse.success_response(
            message="连接成功" if success else "连接失败",
            data=StorageEngineTestResult(
                success=success,
                message="连接成功" if success else "连接失败",
                latency=round(latency, 2) if success else None
            )
        )
    except Exception as e:
        return BaseResponse.success_response(
            message=f"连接测试失败: {str(e)}",
            data=StorageEngineTestResult(
                success=False,
                message=f"连接测试失败: {str(e)}",
                latency=None
            )
        )


@router.put("/{storage_id}/default", response_model=BaseResponse)
async def set_default_storage_engine(
    storage_id: int,
    db: AsyncSession = Depends(get_db)
):
    """设置默认存储引擎"""
    try:
        storage = await StorageService.set_default(db, storage_id)
        if not storage:
            raise AppException(
                status_code=404,
                detail="存储引擎不存在",
                error_code=ERROR_CODES["STORAGE_NOT_FOUND"]
            )
        
        return BaseResponse.success_response(
            data=StorageEngineResponse.model_validate(storage)
        )
    except AppException:
        raise
    except Exception as e:
        raise AppException(
            status_code=400,
            detail=f"设置失败: {str(e)}",
            error_code="STORAGE_SET_DEFAULT_FAILED"
        )


@router.get("/{storage_id}/usage", response_model=BaseResponse)
async def get_storage_usage(
    storage_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取存储引擎使用情况"""
    # 从缓存获取存储引擎配置
    storage_engine = storage_cache.get_storage_engine(storage_id)
    if not storage_engine:
        raise AppException(
            status_code=404,
            detail="存储引擎不存在或未激活",
            error_code=ERROR_CODES["STORAGE_NOT_FOUND"]
        )
    
    # 从缓存获取存储实例
    storage_instance = storage_cache.get_storage(storage_id)
    if not storage_instance:
        raise AppException(
            status_code=404,
            detail="存储引擎实例未加载",
            error_code=ERROR_CODES["STORAGE_NOT_FOUND"]
        )
    
    try:
        # 使用缓存的实例获取使用情况
        usage = await storage_instance.get_usage()
        
        # 计算使用百分比
        usage_percent = None
        if storage_engine.max_capacity and storage_engine.max_capacity > 0:
            usage_percent = (usage["used_capacity"] / storage_engine.max_capacity) * 100
        
        return BaseResponse.success_response(
            data=StorageEngineUsage(
                used_capacity=usage["used_capacity"],
                max_capacity=storage_engine.max_capacity,
                usage_percent=round(usage_percent, 2) if usage_percent else None,
                file_count=usage.get("file_count"),
                available=usage.get("available", True)
            )
        )
    except Exception as e:
        return BaseResponse.success_response(
            data=StorageEngineUsage(
                used_capacity=storage_engine.used_capacity,
                max_capacity=storage_engine.max_capacity,
                usage_percent=None,
                file_count=None,
                available=False
            )
        )
