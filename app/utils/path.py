from datetime import datetime
from typing import Optional


def generate_storage_path(
    filename: str,
    path_rule: str = "uploads/{date}/{filename}.{ext}",
    custom_date: Optional[datetime] = None,
    sha256_hash: Optional[str] = None
) -> str:
    """
    根据路径规则生成存储路径
    
    Args:
        filename: 原始文件名
        path_rule: 路径规则，支持 {date}, {filename}, {ext}, {year}, {month}, {day}, {sha256}
        custom_date: 自定义日期，None则使用当前日期
        sha256_hash: SHA256哈希值，如果提供则优先使用作为文件名
        
    Returns:
        生成的存储路径
    """
    date = custom_date or datetime.now()
    
    # 提取文件名和扩展名
    if "." in filename:
        name, ext = filename.rsplit(".", 1)
    else:
        name, ext = filename, ""
    
    # 如果提供了SHA256哈希值，使用它作为文件名
    filename_to_use = sha256_hash if sha256_hash else name
    
    # 替换路径规则中的变量
    path = path_rule.format(
        date=date.strftime("%Y%m%d"),
        year=date.strftime("%Y"),
        month=date.strftime("%m"),
        day=date.strftime("%d"),
        filename=filename_to_use,
        ext=ext.lower() if ext else "",
        sha256=sha256_hash or ""
    )
    
    return path
