"""
系统配置API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.services.config import ConfigService
from app.schemas.config import (
    SystemConfigResponse,
    SystemConfigUpdate,
    SystemConfigBatchUpdate,
    SystemSettings
)
from app.schemas.response import BaseResponse
from app.core.config_cache import config_cache
from app.core.exceptions import AppException


router = APIRouter(prefix="/config", tags=["系统配置"])


@router.get("", response_model=BaseResponse)
async def get_all_configs(
    db: AsyncSession = Depends(get_db)
):
    """获取所有系统配置"""
    configs = await ConfigService.get_all(db)
    return BaseResponse.success_response(data=configs)


@router.put("/batch", response_model=BaseResponse)
async def batch_update_configs(
    update: SystemConfigBatchUpdate,
    db: AsyncSession = Depends(get_db)
):
    """批量更新配置"""
    await ConfigService.update_multiple(db, update.configs)
    
    # 更新缓存
    await config_cache.update(update.configs)
    
    return BaseResponse.success_response(message="批量更新配置成功")


@router.get("/{key}", response_model=BaseResponse)
async def get_config(
    key: str,
    db: AsyncSession = Depends(get_db)
):
    """获取指定配置"""
    value = await ConfigService.get(db, key)
    if value is None:
        raise AppException(
            status_code=404,
            detail="配置不存在",
            error_code="CONFIG_NOT_FOUND"
        )
    return BaseResponse.success_response(data={"key": key, "value": value})


@router.put("/{key}", response_model=BaseResponse)
async def update_config(
    key: str,
    update: SystemConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新指定配置"""
    config = await ConfigService.set(db, key, update.value)
    
    # 更新缓存
    await config_cache.set(key, update.value)
    
    return BaseResponse.success_response(
        message="配置更新成功",
        data=SystemConfigResponse.model_validate(config)
    )


@router.get("/settings", response_model=BaseResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db)
):
    """获取系统设置（结构化的配置）"""
    # 从缓存获取配置
    settings_data = SystemSettings(
        max_upload_size=await config_cache.get_max_upload_size(),
        allowed_image_types=await config_cache.get_allowed_image_types(),
        thumbnail_width=await config_cache.get_thumbnail_width(),
        thumbnail_height=await config_cache.get_thumbnail_height(),
        system_domain=await config_cache.get_system_domain()
    )
    
    return BaseResponse.success_response(data=settings_data)


@router.put("/settings", response_model=BaseResponse)
async def update_settings(
    settings_update: SystemSettings,
    db: AsyncSession = Depends(get_db)
):
    """更新系统设置"""
    # 转换为配置字典
    configs = {
        "max_upload_size": str(settings_update.max_upload_size),
        "allowed_image_types": settings_update.allowed_image_types,
        "thumbnail_width": str(settings_update.thumbnail_width),
        "thumbnail_height": str(settings_update.thumbnail_height),
        "system_domain": settings_update.system_domain,
    }
    
    # 更新数据库
    await ConfigService.update_multiple(db, configs)
    
    # 更新缓存
    await config_cache.update(configs)
    
    return BaseResponse.success_response(message="系统设置更新成功")


@router.delete("/{key}", response_model=BaseResponse)
async def delete_config(
    key: str,
    db: AsyncSession = Depends(get_db)
):
    """删除指定配置"""
    success = await ConfigService.delete(db, key)
    if not success:
        raise AppException(
            status_code=404,
            detail="配置不存在",
            error_code="CONFIG_NOT_FOUND"
        )
    
    # 从缓存中删除
    await config_cache.delete(key)
    
    return BaseResponse.deleted_response()


@router.post("/reload", response_model=BaseResponse)
async def reload_configs(
    db: AsyncSession = Depends(get_db)
):
    """重新加载配置（从数据库）"""
    await config_cache.reload_from_db(db)
    return BaseResponse.success_response(message="配置重新加载成功")
