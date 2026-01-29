from pathlib import Path
from app.core.storages.base import StorageBase
from app.config.settings import settings


class LocalStorage(StorageBase):
    """本地文件存储实现"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        # base_path参数与settings.UPLOAD_DIR拼接
        config_base_path = config.get("base_path", "")
        self.base_path = Path(settings.UPLOAD_DIR) / config_base_path
        self.base_url = config.get("base_url", "http://localhost:8000/uploads")
        # 确保目录存在
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def upload(self, file_data: bytes, file_path: str) -> str:
        """上传文件到本地存储"""
        full_path = self.base_path / file_path
        # 确保目录存在
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 写入文件
        with open(full_path, "wb") as f:
            f.write(file_data)
        print(f"[LocalStorage] 文件已保存到: {full_path}")
        # 返回访问URL
        return f"{self.base_url.rstrip('/')}/{file_path}"
    
    async def download(self, file_path: str) -> bytes:
        """从本地存储下载文件"""
        full_path = self.base_path / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        with open(full_path, "rb") as f:
            return f.read()
    
    async def delete(self, file_path: str) -> bool:
        """删除本地存储的文件"""
        full_path = self.base_path / file_path
        if full_path.exists():
            full_path.unlink()
            return True
        return False
    
    async def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        full_path = self.base_path / file_path
        return full_path.exists()
    
    async def get_url(self, file_path: str) -> str:
        """获取文件访问URL"""
        return f"{self.base_url.rstrip('/')}/{file_path}"
    
    async def test_connection(self) -> bool:
        """测试本地存储连接（检查目录是否可写）"""
        try:
            test_file = self.base_path / ".test_write"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except Exception:
            return False
    
    async def get_usage(self) -> dict:
        """获取本地存储使用情况"""
        total_size = 0
        file_count = 0
        
        if self.base_path.exists():
            for file_path in self.base_path.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
        
        return {
            "used_capacity": total_size,
            "file_count": file_count,
            "available": True
        }
