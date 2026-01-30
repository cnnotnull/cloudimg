"""
缩略图生成工具
"""
import os
from io import BytesIO
from typing import Tuple, Optional
from PIL import Image as PILImage


def generate_thumbnail(image_data: bytes, save_path: str, width: int = 300, height: int = 300) -> str:
    """
    生成图片缩略图并保存到本地
    
    Args:
        image_data: 原始图片数据（字节）
        save_path: 保存路径（相对路径）
        width: 缩略图宽度
        height: 缩略图高度
        
    Returns:
        缩略图文件扩展名（'webp' 或 'jpg'）
    """
    # 打开图片
    img = PILImage.open(BytesIO(image_data))
    
    # 转换为RGB模式（如果需要）
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    
    # 计算缩放比例，保持宽高比
    original_width, original_height = img.size
    ratio = min(width / original_width, height / original_height)
    new_width = int(original_width * ratio)
    new_height = int(original_height * ratio)
    
    # 使用高质量缩放
    img.thumbnail((new_width, new_height), PILImage.LANCZOS)
    
    # 确保目录存在
    full_save_path = os.path.abspath(save_path)
    os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
    
    # 优先尝试保存为WebP格式
    try:
        img.save(full_save_path, format='WEBP', quality=85, optimize=True)
        print(f"WebP格式保存成功: {full_save_path}")
        return 'webp'
    except Exception as e:
        # WebP格式失败，回退到JPEG
        print(f"WebP格式保存失败，使用JPEG格式: {str(e)}")
        jpg_path = full_save_path.rsplit('.', 1)[0] + '.jpg'
        img.save(jpg_path, format='JPEG', quality=85, optimize=True)
        # 返回jpg扩展名，并更新save_path
        return 'jpg'


def get_thumbnail_dimensions(original_width: int, original_height: int, max_width: int = 300, max_height: int = 300) -> Tuple[int, int]:
    """
    计算缩略图尺寸（保持宽高比）
    
    Args:
        original_width: 原始宽度
        original_height: 原始高度
        max_width: 最大宽度
        max_height: 最大高度
        
    Returns:
        (缩略图宽度, 缩略图高度)
    """
    ratio = min(max_width / original_width, max_height / original_height)
    return (int(original_width * ratio), int(original_height * ratio))
