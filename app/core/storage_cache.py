"""
存储引擎缓存管理器

负责在内存中缓存激活的存储引擎实例，避免每次操作都查询数据库和重新创建存储实例。
"""
from typing import Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.storage import StorageEngine
from app.core.storages.base import StorageBase
from app.core.storages.factory import StorageFactory


class StorageCache:
    """存储引擎缓存管理器（单例模式）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化缓存"""
        if not self._initialized:
            self._storage_dict: Dict[int, Dict] = {}  # {storage_id: {"engine": StorageEngine, "instance": StorageBase}}
            self._default_storage_id: Optional[int] = None
            self._initialized = True
    
    async def initialize(self, db: AsyncSession):
        """
        初始化缓存，从数据库加载所有激活的存储引擎
        
        Args:
            db: 数据库会话
        """
        print("[CACHE] 正在初始化存储引擎缓存...")
        
        # 清空缓存
        self._storage_dict.clear()
        self._default_storage_id = None
        
        # 查询所有激活的存储引擎
        result = await db.execute(
            select(StorageEngine)
            .where(StorageEngine.is_active == True)
            .order_by(StorageEngine.id)
        )
        storage_engines = result.scalars().all()
        
        # 创建存储实例并缓存
        for storage in storage_engines:
            try:
                # 创建存储实例
                storage_config = {
                    "name": storage.name,
                    "type": storage.type,
                    **storage.config
                }
                storage_instance = StorageFactory.create(
                    storage.type,
                    storage_config
                )
                
                # 缓存存储引擎和实例
                self._storage_dict[storage.id] = {
                    "engine": storage,
                    "instance": storage_instance
                }
                
                # 记录默认存储引擎
                if storage.is_default:
                    self._default_storage_id = storage.id
                
                print(f"[CACHE] ✓ 加载存储引擎: {storage.name} (ID: {storage.id}, 类型: {storage.type})")
            except Exception as e:
                print(f"[CACHE] ✗ 加载存储引擎失败: {storage.name} (ID: {storage.id}), 错误: {str(e)}")
        
        print(f"[CACHE] 存储引擎缓存初始化完成，共加载 {len(self._storage_dict)} 个存储引擎")
        print(f"[CACHE] 默认存储引擎ID: {self._default_storage_id}")
    
    def get_storage(self, storage_id: int) -> Optional[StorageBase]:
        """
        获取存储引擎实例
        
        Args:
            storage_id: 存储引擎ID
            
        Returns:
            存储引擎实例，如果不存在返回None
        """
        cache_item = self._storage_dict.get(storage_id)
        if cache_item:
            return cache_item["instance"]
        return None
    
    def get_storage_engine(self, storage_id: int) -> Optional[StorageEngine]:
        """
        获取存储引擎配置对象
        
        Args:
            storage_id: 存储引擎ID
            
        Returns:
            存储引擎配置对象，如果不存在返回None
        """
        cache_item = self._storage_dict.get(storage_id)
        if cache_item:
            return cache_item["engine"]
        return None
    
    def get_default_storage(self) -> Optional[StorageBase]:
        """
        获取默认存储引擎实例
        
        Returns:
            默认存储引擎实例，如果不存在返回None
        """
        if self._default_storage_id:
            return self.get_storage(self._default_storage_id)
        return None
    
    def get_default_storage_engine(self) -> Optional[StorageEngine]:
        """
        获取默认存储引擎配置对象
        
        Returns:
            默认存储引擎配置对象，如果不存在返回None
        """
        if self._default_storage_id:
            return self.get_storage_engine(self._default_storage_id)
        return None
    
    def get_default_storage_id(self) -> Optional[int]:
        """
        获取默认存储引擎ID
        
        Returns:
            默认存储引擎ID，如果不存在返回None
        """
        return self._default_storage_id
    
    def add_storage(self, storage: StorageEngine):
        """
        添加存储引擎到缓存
        
        Args:
            storage: 存储引擎配置对象
        """
        try:
            # 创建存储实例
            storage_config = {
                "name": storage.name,
                "type": storage.type,
                **storage.config
            }
            storage_instance = StorageFactory.create(
                storage.type,
                storage_config
            )
            
            # 添加到缓存
            self._storage_dict[storage.id] = {
                "engine": storage,
                "instance": storage_instance
            }
            
            # 如果是默认存储引擎，更新默认ID
            if storage.is_default:
                self._default_storage_id = storage.id
            
            print(f"[CACHE] ✓ 添加存储引擎: {storage.name} (ID: {storage.id})")
        except Exception as e:
            print(f"[CACHE] ✗ 添加存储引擎失败: {storage.name} (ID: {storage.id}), 错误: {str(e)}")
            raise
    
    def update_storage(self, storage: StorageEngine):
        """
        更新存储引擎缓存
        
        Args:
            storage: 存储引擎配置对象
        """
        # 如果存储引擎在缓存中，移除旧的
        if storage.id in self._storage_dict:
            del self._storage_dict[storage.id]
        
        # 如果是激活状态，重新添加
        if storage.is_active:
            self.add_storage(storage)
        else:
            # 如果是默认存储引擎被禁用，清除默认ID
            if storage.id == self._default_storage_id:
                self._default_storage_id = None
                print(f"[CACHE] 默认存储引擎已禁用 (ID: {storage.id})")
        
        print(f"[CACHE] ✓ 更新存储引擎: {storage.name} (ID: {storage.id}, 激活: {storage.is_active})")
    
    def delete_storage(self, storage_id: int):
        """
        从缓存中删除存储引擎
        
        Args:
            storage_id: 存储引擎ID
        """
        if storage_id in self._storage_dict:
            storage = self._storage_dict[storage_id]["engine"]
            del self._storage_dict[storage_id]
            
            # 如果是默认存储引擎被删除，清除默认ID
            if storage_id == self._default_storage_id:
                self._default_storage_id = None
            
            print(f"[CACHE] ✓ 删除存储引擎: {storage.name} (ID: {storage_id})")
    
    def update_default_storage(self, storage_id: int):
        """
        更新默认存储引擎
        
        Args:
            storage_id: 新的默认存储引擎ID
        """
        # 清除旧的默认标记
        for sid, cache_item in self._storage_dict.items():
            if sid != storage_id:
                cache_item["engine"].is_default = False
        
        # 设置新的默认存储引擎
        self._default_storage_id = storage_id
        if storage_id in self._storage_dict:
            self._storage_dict[storage_id]["engine"].is_default = True
        
        print(f"[CACHE] ✓ 更新默认存储引擎: {storage_id}")
    
    def get_all_storages(self) -> Dict[int, StorageBase]:
        """
        获取所有存储引擎实例
        
        Returns:
            所有存储引擎实例的字典 {storage_id: StorageBase}
        """
        return {
            storage_id: cache_item["instance"]
            for storage_id, cache_item in self._storage_dict.items()
        }
    
    def get_all_storage_engines(self) -> Dict[int, StorageEngine]:
        """
        获取所有存储引擎配置对象
        
        Returns:
            所有存储引擎配置对象的字典 {storage_id: StorageEngine}
        """
        return {
            storage_id: cache_item["engine"]
            for storage_id, cache_item in self._storage_dict.items()
        }
    
    def storage_exists(self, storage_id: int) -> bool:
        """
        检查存储引擎是否在缓存中
        
        Args:
            storage_id: 存储引擎ID
            
        Returns:
            是否存在
        """
        return storage_id in self._storage_dict
    
    def clear(self):
        """清空缓存"""
        self._storage_dict.clear()
        self._default_storage_id = None
        print("[CACHE] ✓ 缓存已清空")
    
    def get_cache_info(self) -> dict:
        """
        获取缓存信息
        
        Returns:
            缓存信息字典
        """
        return {
            "total_count": len(self._storage_dict),
            "default_storage_id": self._default_storage_id,
            "storage_ids": list(self._storage_dict.keys()),
            "storage_types": {
                sid: cache_item["engine"].type
                for sid, cache_item in self._storage_dict.items()
            }
        }


# 创建全局单例实例
storage_cache = StorageCache()
