import hashlib
from typing import Optional
from fastapi import UploadFile
from app.config.settings import settings


def calculate_md5(data: bytes) -> str:
    """计算文件的MD5哈希值"""
    return hashlib.md5(data).hexdigest()


def calculate_sha256(data: bytes) -> str:
    """计算文件的SHA256哈希值"""
    return hashlib.sha256(data).hexdigest()


def validate_image_file(file: UploadFile, max_size: Optional[int] = None, allowed_types: Optional[list] = None) -> tuple[bool, Optional[str]]:
    """
    验证图片文件
    
    Args:
        file: 上传的文件
        max_size: 最大文件大小（字节），None使用默认值
        allowed_types: 允许的文件类型列表，None使用默认值
        
    Returns:
        (是否有效, 错误信息)
    """
    # 检查文件类型
    types_to_check = allowed_types or settings.ALLOWED_IMAGE_TYPES
    if file.content_type not in types_to_check:
        return False, f"不支持的文件类型: {file.content_type}，支持的格式: {', '.join(types_to_check)}"
    
    # 检查文件大小（注意：这里只能检查content_length，实际大小需要读取后验证）
    max_size = max_size or settings.MAX_UPLOAD_SIZE
    if file.size and file.size > max_size:
        return False, f"文件大小超过限制: {file.size} > {max_size}"
    
    return True, None


def get_file_extension(filename: str) -> str:
    """获取文件扩展名（不含点）"""
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def get_image_info(data: bytes) -> dict:
    """
    获取图片信息（尺寸等）
    
    Args:
        data: 图片二进制数据
        
    Returns:
        包含width, height等信息的字典
    """
    try:
        from PIL import Image
        from io import BytesIO
        
        img = Image.open(BytesIO(data))
        return {
            "width": img.width,
            "height": img.height,
            "format": img.format,
            "mode": img.mode
        }
    except Exception:
        return {
            "width": None,
            "height": None,
            "format": None,
            "mode": None
        }
