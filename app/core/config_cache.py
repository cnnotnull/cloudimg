"""
系统配置缓存
"""
from typing import Optional, Dict
import asyncio


class ConfigCache:
    """系统配置缓存"""
    
    def __init__(self):
        """初始化配置缓存"""
        self._cache: Dict[str, str] = {}
        self._lock = asyncio.Lock()
    
    async def initialize(self, configs: Dict[str, str]) -> None:
        """
        初始化配置缓存
        
        Args:
            configs: 配置字典 {key: value}
        """
        async with self._lock:
            self._cache = configs.copy()
    
    async def get(self, key: str, default: str = "") -> str:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self._cache.get(key, default)
    
    async def get_int(self, key: str, default: int = 0) -> int:
        """获取整数类型的配置值"""
        value = await self.get(key)
        try:
            return int(value) if value else default
        except (ValueError, TypeError):
            return default
    
    async def get_bool(self, key: str, default: bool = False) -> bool:
        """获取布尔类型的配置值"""
        value = await self.get(key)
        if not value:
            return default
        return value.lower() in ('true', '1', 'yes', 'on')
    
    async def set(self, key: str, value: str) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        async with self._lock:
            self._cache[key] = value
    
    async def update(self, configs: Dict[str, str]) -> None:
        """
        批量更新配置
        
        Args:
            configs: 配置字典 {key: value}
        """
        async with self._lock:
            self._cache.update(configs)
    
    async def delete(self, key: str) -> None:
        """
        删除配置
        
        Args:
            key: 配置键
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def get_all(self) -> Dict[str, str]:
        """
        获取所有配置
        
        Returns:
            配置字典 {key: value}
        """
        return self._cache.copy()
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    async def reload_from_db(self, db) -> None:
        """
        从数据库重新加载配置
        
        Args:
            db: 数据库会话
        """
        from app.services.config import ConfigService
        configs = await ConfigService.get_all(db)
        await self.initialize(configs)
    
    # 便捷方法 - 获取特定配置
    async def get_max_upload_size(self) -> int:
        """获取最大上传大小"""
        return await self.get_int("max_upload_size", 10 * 1024 * 1024)
    
    async def get_allowed_image_types(self) -> str:
        """获取允许的图片类型"""
        return await self.get("allowed_image_types", "image/jpeg,image/png,image/gif,image/webp")
    
    async def get_thumbnail_width(self) -> int:
        """获取缩略图宽度"""
        return await self.get_int("thumbnail_width", 300)
    
    async def get_thumbnail_height(self) -> int:
        """获取缩略图高度"""
        return await self.get_int("thumbnail_height", 300)
    
    async def get_system_domain(self) -> str:
        """获取系统访问域名"""
        return await self.get("system_domain", "http://localhost:8000")


# 创建全局配置缓存实例
config_cache = ConfigCache()
