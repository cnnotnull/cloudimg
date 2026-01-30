import time
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func

from app.models.storage import StorageEngine
from app.core.storages.factory import StorageFactory
from app.core.storage_cache import storage_cache
from app.core.exceptions import AppException, ERROR_CODES


class StorageService:
    """存储引擎服务"""
    
    @staticmethod
    async def get_all(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[StorageEngine]:
        """获取所有存储引擎（优先从缓存获取）"""
        # 如果查询的是激活的存储引擎，优先从缓存获取
        if is_active is True:
            # 从缓存获取所有存储引擎
            cached_storages = storage_cache.get_all_storage_engines()
            if cached_storages:
                # 应用分页
                storage_list = list(cached_storages.values())
                # 按创建时间降序排序
                storage_list.sort(key=lambda x: x.created_at, reverse=True)
                # 应用分页
                total = len(storage_list)
                if skip >= total:
                    return []
                return storage_list[skip:skip + limit]
        
        # 其他情况或缓存为空，从数据库查询
        query = select(StorageEngine)
        
        if is_active is not None:
            query = query.where(StorageEngine.is_active == is_active)
        
        query = query.offset(skip).limit(limit).order_by(StorageEngine.created_at.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())
    
    @staticmethod
    async def get_by_id(db: AsyncSession, storage_id: int, from_cache: bool = True) -> Optional[StorageEngine]:
        """根据ID获取存储引擎（优先从缓存获取）"""
        # 先从缓存获取（仅用于只读操作）
        if from_cache:
            cached_storage = storage_cache.get_storage_engine(storage_id)
            if cached_storage:
                return cached_storage
        
        # 缓存中不存在或需要从数据库获取，从数据库查询
        result = await db.execute(
            select(StorageEngine).where(StorageEngine.id == storage_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_default(db: AsyncSession) -> Optional[StorageEngine]:
        """获取默认存储引擎（优先从缓存获取）"""
        # 先从缓存获取
        cached_storage = storage_cache.get_default_storage_engine()
        if cached_storage:
            return cached_storage
        
        # 缓存中不存在，从数据库查询
        result = await db.execute(
            select(StorageEngine)
            .where(StorageEngine.is_default == True)
            .where(StorageEngine.is_active == True)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create(db: AsyncSession, storage_data: dict) -> StorageEngine:
        """创建存储引擎"""
        # 如果是第一个存储引擎，自动设为默认
        count_result = await db.execute(select(func.count(StorageEngine.id)))
        count = count_result.scalar()
        is_default = count == 0
        
        # 如果设为默认，需要取消其他默认
        if is_default:
            await db.execute(
                update(StorageEngine).values(is_default=False)
            )
        
        storage = StorageEngine(
            name=storage_data["name"],
            type=storage_data["type"],
            config=storage_data["config"],
            path_rule=storage_data.get("path_rule", "uploads/{date}/{filename}.{ext}"),
            max_capacity=storage_data.get("max_capacity"),
            is_active=storage_data.get("is_active", True),
            is_default=is_default
        )
        
        db.add(storage)
        
        # 刷新以获取生成的ID（用于缓存）
        await db.flush()
        await db.refresh(storage)
        
        # 添加到缓存（如果失败，数据库事务会回滚）
        if storage.is_active:
            try:
                storage_cache.add_storage(storage)
            except Exception as e:
                # 缓存添加失败，抛出异常让数据库事务回滚
                raise AppException(
                    status_code=400,
                    detail=f"创建存储实例失败: {str(e)}",
                    error_code="STORAGE_INSTANCE_CREATE_FAILED"
                )
        
        # 提交数据库事务
        await db.commit()
        await db.refresh(storage)
        
        return storage
    
    @staticmethod
    async def update(
        db: AsyncSession,
        storage_id: int,
        storage_data: dict
    ) -> Optional[StorageEngine]:
        """
        更新存储引擎（只允许更新名称、状态和容量）
        
        Args:
            db: 数据库会话
            storage_id: 存储引擎ID
            storage_data: 更新数据，包含name、is_active、max_capacity字段
            
        Returns:
            更新后的存储引擎实例
        """
        storage = await StorageService.get_by_id(db, storage_id, from_cache=False)
        if not storage:
            return None
        
        # 更新名称
        if "name" in storage_data and storage_data["name"] is not None:
            storage.name = storage_data["name"]
        
        # 更新状态
        if "is_active" in storage_data and storage_data["is_active"] is not None:
            storage.is_active = storage_data["is_active"]
        
        # 更新容量（必须大于已使用容量，或设置为None表示无限制）
        if "max_capacity" in storage_data:
            new_capacity = storage_data["max_capacity"]
            if new_capacity is not None and new_capacity < storage.used_capacity:
                raise AppException(
                    status_code=400,
                    detail=f"容量设置无效：新容量 ({new_capacity} 字节) 必须大于已使用容量 ({storage.used_capacity} 字节)",
                    error_code="INVALID_CAPACITY"
                )
            storage.max_capacity = new_capacity
        
        await db.commit()
        await db.refresh(storage)
        
        # 更新缓存
        storage_cache.update_storage(storage)
        
        return storage
    
    @staticmethod
    async def delete(db: AsyncSession, storage_id: int) -> bool:
        """删除存储引擎"""
        storage = await StorageService.get_by_id(db, storage_id, from_cache=False)
        if not storage:
            return False
        
        # 检查是否有未删除的图片使用此存储引擎
        from app.models.image import Image
        count_result = await db.execute(
            select(func.count(Image.id))
            .where(Image.storage_engine_id == storage_id)
            .where(Image.is_deleted == False)
        )
        image_count = count_result.scalar()
        
        if image_count > 0:
            raise AppException(
                status_code=400,
                detail=f"无法删除存储引擎，仍有 {image_count} 张图片使用此存储引擎",
                error_code="STORAGE_IN_USE"
            )
        
        # 硬删除所有已软删除的图片记录（避免外键约束冲突）
        deleted_images = await db.execute(
            select(Image).where(Image.storage_engine_id == storage_id).where(Image.is_deleted == True)
        )
        for img in deleted_images.scalars().all():
            await db.delete(img)
        
        # 从缓存中删除
        storage_cache.delete_storage(storage_id)
        
        await db.delete(storage)
        await db.commit()
        return True
    
    @staticmethod
    async def set_default(db: AsyncSession, storage_id: int) -> Optional[StorageEngine]:
        """设置默认存储引擎"""
        storage = await StorageService.get_by_id(db, storage_id, from_cache=False)
        if not storage:
            return None
        
        if not storage.is_active:
            raise AppException(
                status_code=400,
                detail="无法将非激活的存储引擎设为默认",
                error_code="STORAGE_DISABLED"
            )
        
        # 取消其他默认
        await db.execute(
            update(StorageEngine)
            .where(StorageEngine.id != storage_id)
            .values(is_default=False)
        )
        
        # 设置当前为默认
        storage.is_default = True
        await db.commit()
        await db.refresh(storage)
        
        # 更新缓存中的默认存储引擎
        storage_cache.update_default_storage(storage_id)
        
        return storage
    
    @staticmethod
    async def test_connection(db: AsyncSession, storage_id: int) -> dict:
        """测试存储引擎连接"""
        storage = await StorageService.get_by_id(db, storage_id)
        # test_connection可以使用缓存，因为不需要修改数据库
        
        try:
            # 创建存储实例
            storage_instance = StorageFactory.create(
                storage.type,
                {"name": storage.name, "type": storage.type, **storage.config}
            )
            
            # 测试连接
            start_time = time.time()
            success = await storage_instance.test_connection()
            latency = (time.time() - start_time) * 1000  # 转换为毫秒
            
            return {
                "success": success,
                "message": "连接成功" if success else "连接失败",
                "latency": round(latency, 2) if success else None
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}",
                "latency": None
            }
    
    @staticmethod
    async def get_usage(db: AsyncSession, storage_id: int) -> dict:
        """获取存储引擎使用情况"""
        storage = await StorageService.get_by_id(db, storage_id)
        # get_usage可以使用缓存，因为不需要修改数据库
        
        try:
            # 创建存储实例
            storage_instance = StorageFactory.create(
                storage.type,
                {"name": storage.name, "type": storage.type, **storage.config}
            )
            
            # 获取使用情况
            usage = await storage_instance.get_usage()
            
            # 计算使用百分比
            usage_percent = None
            if storage.max_capacity and storage.max_capacity > 0:
                usage_percent = (usage["used_capacity"] / storage.max_capacity) * 100
            
            return {
                "used_capacity": usage["used_capacity"],
                "max_capacity": storage.max_capacity,
                "usage_percent": round(usage_percent, 2) if usage_percent else None,
                "file_count": usage.get("file_count"),
                "available": usage.get("available", True)
            }
        except Exception as e:
            return {
                "used_capacity": storage.used_capacity,
                "max_capacity": storage.max_capacity,
                "usage_percent": None,
                "file_count": None,
                "available": False
            }
