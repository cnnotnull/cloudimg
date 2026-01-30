from typing import Optional
from app.core.storages.base import StorageBase
from app.core.storages.local import LocalStorage
from app.core.storages.s3 import S3Storage
from app.core.storages.aliyun_oss import AliyunOSSStorage


class StorageFactory:
    """存储引擎工厂类"""
    
    _storage_types: dict[str, type[StorageBase]] = {
        "local": LocalStorage,
        "s3": S3Storage,  # AWS S3及兼容服务（MinIO、R2等）
        "aliyun_oss": AliyunOSSStorage,  # 阿里云OSS
        # 后续可以添加其他存储类型
        # "cos": COSStorage,
        # "r2": R2Storage,
        # "tencent_cos": TencentCOSSStorage,
        # "qiniu_kodo": QiniuKodoStorage,
    }
    
    @classmethod
    def create(cls, storage_type: str, config: dict) -> StorageBase:
        """
        创建存储引擎实例
        
        Args:
            storage_type: 存储类型 (local, s3, oss, cos, r2)
            config: 存储配置
            
        Returns:
            存储引擎实例
            
        Raises:
            ValueError: 不支持的存储类型
        """
        if storage_type not in cls._storage_types:
            raise ValueError(f"不支持的存储类型: {storage_type}")
        
        storage_class = cls._storage_types[storage_type]
        return storage_class(config)
    
    @classmethod
    def register(cls, storage_type: str, storage_class: type[StorageBase]):
        """
        注册新的存储类型
        
        Args:
            storage_type: 存储类型名称
            storage_class: 存储类
        """
        cls._storage_types[storage_type] = storage_class
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """获取支持的存储类型列表"""
        return list(cls._storage_types.keys())
