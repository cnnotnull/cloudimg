from typing import Any, Dict, Optional, Set
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """ORM基类，提供通用功能"""

    def to_dict(self, exclude: Optional[Set[str]] = None) -> Dict[str, Any]:
        """
        将模型实例转换为字典
        
        Args:
            exclude: 要排除的字段集合
            
        Returns:
            模型数据的字典表示
        """
        exclude = exclude or set()
        result = {}
        
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # 处理 datetime 对象
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Base":
        """
        从字典创建模型实例
        
        Args:
            data: 包含模型数据的字典
            
        Returns:
            模型实例
        """
        # 过滤掉不存在的字段
        valid_fields = {k: v for k, v in data.items() if hasattr(cls, k)}
        return cls(**valid_fields)
    
    def update_from_dict(self, data: Dict[str, Any], exclude: Optional[Set[str]] = None) -> None:
        """
        从字典更新模型实例
        
        Args:
            data: 包含更新数据的字典
            exclude: 要排除的字段集合
        """
        exclude = exclude or set()
        for key, value in data.items():
            if key not in exclude and hasattr(self, key):
                setattr(self, key, value)
    
    def __eq__(self, other: Any) -> bool:
        """比较两个模型实例是否相等（基于主键）"""
        if not isinstance(other, self.__class__):
            return False
        
        # 获取主键
        pk_columns = [col.name for col in self.__table__.primary_key.columns]
        if not pk_columns:
            return id(self) == id(other)
        
        return all(
            getattr(self, pk) == getattr(other, pk)
            for pk in pk_columns
        )
    
    def __hash__(self) -> int:
        """返回对象的哈希值（基于主键）"""
        pk_columns = [col.name for col in self.__table__.primary_key.columns]
        if not pk_columns:
            return id(self)
        
        pk_values = tuple(getattr(self, pk) for pk in pk_columns)
        return hash((self.__class__, pk_values))