from abc import ABC, abstractmethod


class StorageBase(ABC):
    """存储引擎抽象基类"""
    
    def __init__(self, config: dict):
        """
        初始化存储引擎
        
        Args:
            config: 存储配置字典
        """
        self.config = config
        self.name = config.get("name", "unknown")
        self.type = config.get("type", "unknown")
    
    @abstractmethod
    async def upload(self, file_data: bytes, file_path: str) -> str:
        """
        上传文件
        
        Args:
            file_data: 文件二进制数据
            file_path: 存储路径
            
        Returns:
            文件的访问URL
        """
        pass
    
    @abstractmethod
    async def download(self, file_path: str) -> bytes:
        """
        下载文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件二进制数据
        """
        pass
    
    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """
        删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否存在
        """
        pass
    
    @abstractmethod
    async def get_url(self, file_path: str) -> str:
        """
        获取文件访问URL
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件访问URL
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """
        测试存储连接
        
        Returns:
            连接是否成功
        """
        pass
    
    @abstractmethod
    async def get_usage(self) -> dict:
        """
        获取存储使用情况
        
        Returns:
            包含容量信息的字典
        """
        pass