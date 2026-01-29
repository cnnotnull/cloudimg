from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel


class ResponseMessages:
    """响应消息常量"""
    SUCCESS = "操作成功"
    FETCH_SUCCESS = "获取成功"
    CREATE_SUCCESS = "创建成功"
    UPDATE_SUCCESS = "更新成功"
    DELETE_SUCCESS = "删除成功"
    UPLOAD_SUCCESS = "上传成功"
    SET_SUCCESS = "设置成功"
    SYSTEM_HEALTHY = "系统运行正常"


class BaseResponse(BaseModel):
    """基础响应格式"""

    success: bool = True
    message: str = ""
    data: Optional[Any] = None
    error_code: Optional[str] = None
    timestamp: datetime = datetime.now()

    @classmethod
    def success_response(
        cls,
        data: Optional[Any] = None,
        message: Optional[str] = None
    ) -> "BaseResponse":
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 成功消息（默认使用"操作成功"）
            
        Returns:
            BaseResponse实例
        """
        return cls(success=True, message=message or ResponseMessages.SUCCESS, data=data)

    @classmethod
    def success_message(cls, message: str = None) -> "BaseResponse":
        """
        创建仅包含消息的成功响应
        
        Args:
            message: 成功消息（默认使用"操作成功"）
            
        Returns:
            BaseResponse实例
        """
        return cls(success=True, message=message or ResponseMessages.SUCCESS)

    @classmethod
    def error_response(
        cls,
        message: str = "操作失败",
        error_code: Optional[str] = None,
        data: Optional[Any] = None
    ) -> "BaseResponse":
        """
        创建错误响应
        
        Args:
            message: 错误消息
            error_code: 错误码
            data: 响应数据
            
        Returns:
            BaseResponse实例
        """
        return cls(success=False, message=message, error_code=error_code, data=data)

    @classmethod
    def paginated_response(
        cls,
        items: List[Any],
        total: int,
        page: int,
        per_page: int
    ) -> "BaseResponse":
        """
        创建分页响应
        
        Args:
            items: 数据项列表
            total: 总数量
            page: 当前页码
            per_page: 每页数量
            
        Returns:
            BaseResponse实例
        """
        total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
        
        return cls(
            success=True,
            message=ResponseMessages.FETCH_SUCCESS,
            data={
                "items": items,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages
            }
        )

    @classmethod
    def created_response(
        cls,
        data: Optional[Any] = None
    ) -> "BaseResponse":
        """
        创建资源响应
        
        Args:
            data: 响应数据
            
        Returns:
            BaseResponse实例
        """
        return cls(success=True, message=ResponseMessages.CREATE_SUCCESS, data=data)

    @classmethod
    def updated_response(
        cls,
        data: Optional[Any] = None
    ) -> "BaseResponse":
        """
        更新资源响应
        
        Args:
            data: 响应数据
            
        Returns:
            BaseResponse实例
        """
        return cls(success=True, message=ResponseMessages.UPDATE_SUCCESS, data=data)

    @classmethod
    def deleted_response(
        cls,
        deleted_count: Optional[int] = None
    ) -> "BaseResponse":
        """
        删除资源响应
        
        Args:
            deleted_count: 删除数量
            
        Returns:
            BaseResponse实例
        """
        if deleted_count is not None:
            message = f"成功删除 {deleted_count} 项"
            data = {"deleted_count": deleted_count}
        else:
            message = ResponseMessages.DELETE_SUCCESS
            data = None
        
        return cls(success=True, message=message, data=data)

    @classmethod
    def upload_response(
        cls,
        data: Optional[Any] = None
    ) -> "BaseResponse":
        """
        上传成功响应
        
        Args:
            data: 响应数据
            
        Returns:
            BaseResponse实例
        """
        return cls(success=True, message=ResponseMessages.UPLOAD_SUCCESS, data=data)


class PaginatedResponse(BaseResponse):
    """分页响应格式"""

    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


class ErrorResponse(BaseResponse):
    """错误响应格式"""

    success: bool = False
    detail: Optional[str] = None
