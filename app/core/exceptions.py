from typing import Any, Optional
from fastapi import HTTPException


class AppException(HTTPException):
    """自定义应用异常"""

    def __init__(
        self,
        status_code: int = 400,
        detail: Any = None,
        error_code: Optional[str] = None,
        headers: Optional[dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


# 定义错误码
ERROR_CODES = {
    # 通用错误
    "INVALID_REQUEST": "请求参数无效",
    "UNAUTHORIZED": "未授权访问",
    "FORBIDDEN": "禁止访问",
    "NOT_FOUND": "资源不存在",
    "INTERNAL_ERROR": "服务器内部错误",
    # 存储相关错误
    "STORAGE_NOT_FOUND": "存储引擎不存在",
    "STORAGE_DISABLED": "存储引擎已禁用",
    "STORAGE_FULL": "存储空间不足",
    "STORAGE_CONNECTION_FAILED": "存储连接失败",
    # 图片相关错误
    "IMAGE_NOT_FOUND": "图片不存在",
    "IMAGE_UPLOAD_FAILED": "图片上传失败",
    "IMAGE_PROCESSING_FAILED": "图片处理失败",
    "IMAGE_DELETE_FAILED": "图片删除失败",
    "INVALID_IMAGE_FORMAT": "无效的图片格式",
    "IMAGE_TOO_LARGE": "图片文件过大",
    # 处理相关错误
    "PROCESSING_CONFIG_NOT_FOUND": "处理配置不存在",
    "PROCESSING_FAILED": "处理失败",
}
