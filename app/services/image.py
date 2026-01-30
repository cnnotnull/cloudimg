from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from fastapi import UploadFile

from app.models.image import Image
from app.services.storage import StorageService
from app.core.storage_cache import storage_cache
from app.core.storages.factory import StorageFactory
from app.utils.file import calculate_md5, calculate_sha256, validate_image_file, get_image_info
from app.utils.path import generate_storage_path
from app.utils.thumbnail import generate_thumbnail, get_thumbnail_dimensions
from app.core.exceptions import AppException, ERROR_CODES
from app.config.settings import settings


class ImageService:
    """图片服务"""
    
    @staticmethod
    async def upload(
        db: AsyncSession,
        file: UploadFile,
        storage_engine_id: Optional[int] = None,
        upload_ip: Optional[str] = None
    ) -> Image:
        """
        上传图片
        
        Args:
            db: 数据库会话
            file: 上传的文件
            storage_engine_id: 存储引擎ID，None则使用默认存储引擎
            upload_ip: 上传IP地址
            
        Returns:
            图片模型实例
        """
        # 读取文件数据
        file_data = await file.read()
        
        # 验证文件
        is_valid, error_msg = validate_image_file(file)
        if not is_valid:
            raise AppException(
                status_code=400,
                detail=error_msg or "文件验证失败",
                error_code=ERROR_CODES["INVALID_IMAGE_FORMAT"]
            )
        
        # 检查文件大小
        if len(file_data) > settings.MAX_UPLOAD_SIZE:
            raise AppException(
                status_code=400,
                detail=f"文件大小超过限制: {len(file_data)} > {settings.MAX_UPLOAD_SIZE}",
                error_code=ERROR_CODES["IMAGE_TOO_LARGE"]
            )
        
        # 计算哈希值
        md5_hash = calculate_md5(file_data)
        sha256_hash = calculate_sha256(file_data)
        
        # 检查是否已存在（通过MD5或SHA256）
        existing_image = await db.execute(
            select(Image).where(
                (Image.md5 == md5_hash) | (Image.sha256 == sha256_hash)
            ).where(Image.is_deleted == False)
        )
        existing = existing_image.scalar_one_or_none()
        # TODO 记录存储数据库，但是图片不再上传云端，直接使用已有路径
        if existing:
            # 如果已存在且未删除，返回现有记录
            return existing
        
        # 获取存储引擎配置
        if storage_engine_id:
            storage = await StorageService.get_by_id(db, storage_engine_id)
            if not storage:
                raise AppException(
                    status_code=404,
                    detail="存储引擎不存在",
                    error_code=ERROR_CODES["STORAGE_NOT_FOUND"]
                )
            if not storage.is_active:
                raise AppException(
                    status_code=400,
                    detail="存储引擎未激活",
                    error_code=ERROR_CODES["STORAGE_DISABLED"]
                )
        else:
            storage = await StorageService.get_default(db)
            if not storage:
                raise AppException(
                    status_code=400,
                    detail="未找到默认存储引擎",
                    error_code="NO_DEFAULT_STORAGE"
                )
        
        # 从缓存获取存储实例
        storage_instance = storage_cache.get_storage(storage.id)
        if not storage_instance:
            raise AppException(
                status_code=500,
                detail=f"存储引擎实例未加载到缓存: {storage.name}",
                error_code="STORAGE_NOT_LOADED"
            )
        
        # 获取图片信息
        image_info = get_image_info(file_data)
        
        # 生成存储路径（使用MD5作为文件名，缩短路径长度）
        storage_path = generate_storage_path(
            file.filename or "image",
            storage.path_rule,
            md5_hash=md5_hash
        )
        
        try:
            original_url = await storage_instance.upload(file_data, storage_path)
        except Exception as e:
            raise AppException(
                status_code=500,
                detail=f"上传失败: {str(e)}",
                error_code=ERROR_CODES["IMAGE_UPLOAD_FAILED"]
            )
        
        # 处理缩略图（保存到本地）
        thumbnail_path = None
        try:
            # 生成缩略图本地保存路径（带webp扩展名）
            from datetime import datetime
            date_path = datetime.now().strftime("%Y%m%d")
            thumbnail_filename = f"{md5_hash}.{settings.THUMBNAIL_WIDTH}x{settings.THUMBNAIL_HEIGHT}.webp"
            thumbnail_save_path = f"{settings.THUMBNAIL_SAVE_PATH}/{date_path}/{thumbnail_filename}"
            print(f"thumbnail_save_path: {thumbnail_save_path}")
            # 生成缩略图并保存到本地
            thumbnail_ext = generate_thumbnail(
                file_data,
                thumbnail_save_path,
                width=settings.THUMBNAIL_WIDTH,
                height=settings.THUMBNAIL_HEIGHT
            )
            
            # 存储相对路径到数据库（使用实际的扩展名）
            if thumbnail_ext == 'webp':
                thumbnail_path = f"{date_path}/{thumbnail_filename}"
            else:
                # 如果保存为jpg，更新文件名
                thumbnail_path = f"{date_path}/{md5_hash}.{settings.THUMBNAIL_WIDTH}x{settings.THUMBNAIL_HEIGHT}.{thumbnail_ext}"
        except Exception as e:
            # 缩略图生成失败不影响主图
            print(f"缩略图生成失败: {str(e)}")
            thumbnail_path = None
        
        # 创建新记录（使用自增ID）
        image = Image(
            md5=md5_hash,
            sha256=sha256_hash,
            original_filename=file.filename or "image",
            storage_filename=storage_path,
            storage_engine_id=storage.id,
            file_size=len(file_data),
            file_type=file.content_type or "image/jpeg",
            width=image_info.get("width"),
            height=image_info.get("height"),
            upload_ip=upload_ip,
            original_url=original_url,
            thumbnail_url=thumbnail_path,
            extra_metadata=image_info
        )
        db.add(image)
        
        # 更新存储引擎使用量
        storage.used_capacity += len(file_data)
        
        await db.commit()
        await db.refresh(image)
        
        return image
    
    @staticmethod
    async def get_by_id(db: AsyncSession, image_id: int) -> Optional[Image]:
        """根据ID获取图片"""
        result = await db.execute(
            select(Image).where(Image.id == image_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_list(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        storage_engine_id: Optional[int] = None,
        file_type: Optional[str] = None,
        is_deleted: Optional[bool] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> tuple[List[Image], int]:
        """
        获取图片列表
        
        Returns:
            (图片列表, 总数)
        """
        query = select(Image)
        count_query = select(Image.id)
        
        conditions = []
        
        if storage_engine_id:
            conditions.append(Image.storage_engine_id == storage_engine_id)
        
        if file_type:
            conditions.append(Image.file_type == file_type)
        
        if is_deleted is not None:
            conditions.append(Image.is_deleted == is_deleted)
        
        if start_date:
            conditions.append(Image.created_at >= start_date)
        
        if end_date:
            conditions.append(Image.created_at <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 获取总数
        total_result = await db.execute(count_query)
        total = len(total_result.scalars().all())
        
        # 获取列表
        query = query.order_by(Image.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        images = list(result.scalars().all())
        
        return images, total
    
    @staticmethod
    async def delete(
        db: AsyncSession,
        image_id: int,
        hard_delete: bool = False
    ) -> bool:
        """
        删除图片
        
        Args:
            db: 数据库会话
            image_id: 图片ID
            hard_delete: 是否硬删除（物理删除文件）
            
        Returns:
            是否删除成功
        """
        image = await ImageService.get_by_id(db, image_id)
        if not image:
            return False
        
        if hard_delete:
            # 硬删除：删除物理文件
            storage_engine = await StorageService.get_by_id(db, image.storage_engine_id)
            if storage_engine:
                try:
                    # 从缓存获取存储实例
                    storage_instance = storage_cache.get_storage(image.storage_engine_id)
                    if storage_instance:
                        await storage_instance.delete(image.storage_filename)
                    
                    # 更新存储引擎使用量
                    storage_engine.used_capacity = max(0, storage_engine.used_capacity - image.file_size)
                except Exception:
                    pass  # 文件可能已不存在
            
            # 删除数据库记录
            await db.delete(image)
        else:
            # 软删除：只标记为已删除
            image.is_deleted = True
        
        await db.commit()
        return True
    
    @staticmethod
    async def batch_delete(
        db: AsyncSession,
        image_ids: List[int],
        hard_delete: bool = False
    ) -> int:
        """
        批量删除图片
        
        Returns:
            成功删除的数量
        """
        count = 0
        for image_id in image_ids:
            if await ImageService.delete(db, image_id, hard_delete):
                count += 1
        return count
