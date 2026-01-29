from typing import List, Optional
from datetime import datetime, date
from fastapi import APIRouter, Depends, UploadFile, File, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.services.image import ImageService
from app.services.storage import StorageService
from app.schemas.image import ImageResponse, ImageUploadResponse, ImageListQuery
from app.schemas.response import BaseResponse
from app.core.exceptions import AppException, ERROR_CODES

router = APIRouter(prefix="/images", tags=["图片管理"])


@router.post("/upload", response_model=BaseResponse, status_code=201)
async def upload_image(
    file: UploadFile = File(...),
    storage_engine_id: Optional[int] = Query(None, description="存储引擎ID，不指定则使用默认"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """上传单张图片"""
    try:
        # 获取客户端IP
        upload_ip = None
        if request and request.client:
            upload_ip = request.client.host
        
        image = await ImageService.upload(
            db=db,
            file=file,
            storage_engine_id=storage_engine_id,
            upload_ip=upload_ip
        )
        
        return BaseResponse.upload_response(
            data=ImageUploadResponse(
                id=image.id,
                md5=image.md5,
                sha256=image.sha256,
                filename=image.original_filename,
                url=image.original_url,
                thumbnail_url=image.thumbnail_url,
                size=image.file_size,
                width=image.width,
                height=image.height
            )
        )
    except AppException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            detail=f"上传失败: {str(e)}",
            error_code=ERROR_CODES["IMAGE_UPLOAD_FAILED"]
        )


@router.post("/upload/batch", response_model=BaseResponse, status_code=201)
async def upload_images_batch(
    files: List[UploadFile] = File(...),
    storage_engine_id: Optional[int] = Query(None, description="存储引擎ID，不指定则使用默认"),
    request: Request = None,
    db: AsyncSession = Depends(get_db)
):
    """批量上传图片"""
    upload_ip = None
    if request and request.client:
        upload_ip = request.client.host
    
    results = []
    errors = []
    
    for file in files:
        try:
            image = await ImageService.upload(
                db=db,
                file=file,
                storage_engine_id=storage_engine_id,
                upload_ip=upload_ip
            )
            results.append(ImageUploadResponse(
                id=image.id,
                md5=image.md5,
                sha256=image.sha256,
                filename=image.original_filename,
                url=image.original_url,
                thumbnail_url=image.thumbnail_url,
                size=image.file_size,
                width=image.width,
                height=image.height
            ))
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return BaseResponse.success_response(
        message=f"成功上传 {len(results)} 张，失败 {len(errors)} 张",
        data={
            "success": results,
            "errors": errors
        }
    )


@router.get("", response_model=BaseResponse)
async def get_images(
    skip: int = Query(0, ge=0, description="跳过数量"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    image_date: Optional[date] = Query(None, description="图片日期，格式：YYYY-MM-DD，为空则返回当天"),
    storage_engine_id: Optional[int] = Query(None, description="存储引擎ID，为空则返回默认存储引擎的数据"),
    file_type: Optional[str] = Query(None, description="文件类型"),
    is_deleted: Optional[bool] = Query(None, description="是否已删除"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取图片列表
    
    Args:
        skip: 跳过数量
        limit: 返回数量
        image_date: 图片日期，为空则返回当天数据
        storage_engine_id: 存储引擎ID，为空则返回默认存储引擎的数据
        file_type: 文件类型
        is_deleted: 是否已删除
    """
    # 处理日期参数：如果为空，默认返回当天的数据
    if image_date is None:
        today = datetime.now().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = datetime.combine(today, datetime.max.time())
    else:
        start_date = datetime.combine(image_date, datetime.min.time())
        end_date = datetime.combine(image_date, datetime.max.time())
    
    # 处理存储引擎ID：如果为空，使用默认存储引擎
    if storage_engine_id is None:
        default_storage = await StorageService.get_default(db)
        if default_storage:
            storage_engine_id = default_storage.id
        else:
            # 如果没有默认存储引擎，不限制存储引擎ID
            storage_engine_id = None
    
    images, total = await ImageService.get_list(
        db=db,
        skip=skip,
        limit=limit,
        storage_engine_id=storage_engine_id,
        file_type=file_type,
        is_deleted=is_deleted,
        start_date=start_date,
        end_date=end_date
    )
    
    page = (skip // limit) + 1 if limit > 0 else 1
    
    return BaseResponse.paginated_response(
        items=[ImageResponse.model_validate(img) for img in images],
        total=total,
        page=page,
        per_page=limit
    )


@router.get("/{image_id}", response_model=BaseResponse)
async def get_image(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取图片详情"""
    image = await ImageService.get_by_id(db, image_id)
    if not image:
        raise AppException(
            status_code=404,
            detail="图片不存在",
            error_code=ERROR_CODES["IMAGE_NOT_FOUND"]
        )
    
    return BaseResponse.success_response(
        data=ImageResponse.model_validate(image)
    )


@router.delete("/{image_id}", response_model=BaseResponse)
async def delete_image(
    image_id: int,
    hard_delete: bool = Query(False, description="是否硬删除（物理删除文件）"),
    db: AsyncSession = Depends(get_db)
):
    """删除图片"""
    try:
        success = await ImageService.delete(db, image_id, hard_delete)
        if not success:
            raise AppException(
                status_code=404,
                detail="图片不存在",
                error_code=ERROR_CODES["IMAGE_NOT_FOUND"]
            )
        
        return BaseResponse.deleted_response()
    except AppException:
        raise
    except Exception as e:
        raise AppException(
            status_code=500,
            detail=f"删除失败: {str(e)}",
            error_code=ERROR_CODES["IMAGE_DELETE_FAILED"]
        )


@router.post("/batch-delete", response_model=BaseResponse)
async def batch_delete_images(
    image_ids: List[int],
    hard_delete: bool = Query(False, description="是否硬删除（物理删除文件）"),
    db: AsyncSession = Depends(get_db)
):
    """批量删除图片"""
    try:
        count = await ImageService.batch_delete(db, image_ids, hard_delete)
        return BaseResponse.deleted_response(deleted_count=count)
    except Exception as e:
        raise AppException(
            status_code=500,
            detail=f"批量删除失败: {str(e)}",
            error_code=ERROR_CODES["IMAGE_DELETE_FAILED"]
        )


@router.get("/{image_id}/info", response_model=BaseResponse)
async def get_image_info(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取图片信息"""
    image = await ImageService.get_by_id(db, image_id)
    if not image:
        raise AppException(
            status_code=404,
            detail="图片不存在",
            error_code=ERROR_CODES["IMAGE_NOT_FOUND"]
        )
    
    return BaseResponse.success_response(
        data=ImageResponse.model_validate(image)
    )
