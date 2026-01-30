"""
系统配置服务
"""
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.config import SystemConfig
from app.core.config_cache import config_cache
from app.core.exceptions import AppException, ERROR_CODES


class ConfigService:
    """系统配置服务"""
    
    # 默认配置
    DEFAULT_CONFIGS = {
        # 文件上传配置
        "max_upload_size": "10485760",  # 10MB
        "allowed_image_types": "image/jpeg,image/png,image/gif,image/webp",
        
        # 缩略图配置
        "thumbnail_width": "300",
        "thumbnail_height": "300",
        
        # 系统访问域名
        "system_domain": "http://localhost:8000",
    }
    
    @staticmethod
    async def get(db: AsyncSession, key: str, from_cache: bool = True) -> Optional[str]:
        """
        获取配置值（优先从缓存获取）
        
        Args:
            db: 数据库会话
            key: 配置键
            from_cache: 是否从缓存获取
            
        Returns:
            配置值，不存在返回None
        """
        # 先从缓存获取
        if from_cache:
            return await config_cache.get(key)
        
        # 从数据库查询
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        config = result.scalar_one_or_none()
        return config.value if config else None
    
    @staticmethod
    async def get_int(db: AsyncSession, key: str, default: int = 0, from_cache: bool = True) -> int:
        """获取整数类型的配置值"""
        value = await ConfigService.get(db, key, from_cache)
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    async def get_bool(db: AsyncSession, key: str, default: bool = False, from_cache: bool = True) -> bool:
        """获取布尔类型的配置值"""
        value = await ConfigService.get(db, key, from_cache)
        if value is None:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    @staticmethod
    async def set(db: AsyncSession, key: str, value: str) -> SystemConfig:
        """
        设置配置值
        
        Args:
            db: 数据库会话
            key: 配置键
            value: 配置值
            
        Returns:
            配置模型实例
        """
        # 查找是否已存在
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        config = result.scalar_one_or_none()
        
        if config:
            # 更新现有配置
            config.value = value
        else:
            # 创建新配置
            config = SystemConfig(key=key, value=value)
            db.add(config)
        
        await db.commit()
        await db.refresh(config)
        
        # 更新缓存
        await config_cache.set(key, value)
        
        return config
    
    @staticmethod
    async def get_all(db: AsyncSession, from_cache: bool = True) -> Dict[str, str]:
        """
        获取所有配置（优先从缓存获取）
        
        Args:
            db: 数据库会话
            from_cache: 是否从缓存获取
            
        Returns:
            配置字典 {key: value}
        """
        # 优先从缓存获取
        if from_cache:
            return await config_cache.get_all()
        
        # 从数据库查询
        result = await db.execute(select(SystemConfig))
        configs = result.scalars().all()
        return {config.key: config.value for config in configs}
    
    @staticmethod
    async def delete(db: AsyncSession, key: str) -> bool:
        """
        删除配置
        
        Args:
            db: 数据库会话
            key: 配置键
            
        Returns:
            是否删除成功
        """
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        config = result.scalar_one_or_none()
        
        if config:
            await db.delete(config)
            await db.commit()
            
            # 从缓存中删除
            await config_cache.delete(key)
            
            return True
        return False
    
    @staticmethod
    async def initialize_defaults(db: AsyncSession) -> int:
        """
        初始化默认配置
        
        Args:
            db: 数据库会话
            
        Returns:
            新增的配置数量
        """
        existing_configs = await ConfigService.get_all(db, from_cache=False)
        count = 0
        
        for key, value in ConfigService.DEFAULT_CONFIGS.items():
            if key not in existing_configs:
                config = SystemConfig(key=key, value=value)
                db.add(config)
                count += 1
        
        if count > 0:
            await db.commit()
        
        return count
    
    @staticmethod
    async def update_multiple(db: AsyncSession, configs: Dict[str, str]) -> None:
        """
        批量更新配置
        
        Args:
            db: 数据库会话
            configs: 配置字典 {key: value}
        """
        for key, value in configs.items():
            result = await db.execute(
                select(SystemConfig).where(SystemConfig.key == key)
            )
            config = result.scalar_one_or_none()
            
            if config:
                config.value = value
            else:
                config = SystemConfig(key=key, value=value)
                db.add(config)
        
        await db.commit()
        
        # 批量更新缓存
        await config_cache.update(configs)
