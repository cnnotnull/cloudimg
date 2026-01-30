"""
阿里云OSS存储引擎
"""
import io
import os
from typing import Optional, Dict, Any
import alibabacloud_oss_v2 as oss
from alibabacloud_oss_v2 import models

from .base import StorageBase


class AliyunOSSStorage(StorageBase):
    """阿里云OSS存储实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化OSS存储引擎
        
        Args:
            config: 配置字典，包含:
                - access_key_id: 访问密钥ID
                - access_key_secret: 访问密钥Secret
                - bucket_name: 存储桶名称
                - region: 区域（如 cn-hangzhou）
                - endpoint: 可选的endpoint
                - prefix: 可选的路径前缀
                - use_ssl: 是否使用HTTPS（默认True）
        """
        self.access_key_id = config.get("access_key_id")
        self.access_key_secret = config.get("access_key_secret")
        self.bucket_name = config.get("bucket_name")
        self.region = config.get("region", "cn-hangzhou")
        self.endpoint = config.get("endpoint")
        self.prefix = config.get("prefix", "").strip("/")
        self.use_ssl = config.get("use_ssl", True)
        
        # 创建凭证提供者
        credentials_provider = oss.credentials.StaticCredentialsProvider(
            self.access_key_id,
            self.access_key_secret
        )
        
        # 加载配置
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider
        cfg.region = self.region
        
        # 如果指定了endpoint，使用自定义endpoint
        if self.endpoint:
            cfg.endpoint = self.endpoint
        
        # 创建OSS客户端
        self.client = oss.Client(cfg)
    
    def _get_full_key(self, key: str) -> str:
        """
        获取完整的对象键
        
        Args:
            key: 对象键
            
        Returns:
            完整的对象键（包含前缀）
        """
        if self.prefix:
            return f"{self.prefix}/{key}".strip("/")
        return key
    
    async def upload(self, data: bytes, key: str, content_type: Optional[str] = None) -> str:
        """
        上传数据到OSS
        
        Args:
            key: 对象键
            data: 要上传的数据
            content_type: 内容类型
            
        Returns:
            对象的URL
        """
        full_key = self._get_full_key(key)
        
        # 构建上传请求
        request = models.PutObjectRequest(
            bucket=self.bucket_name,
            key=full_key,
            body=data,
        )
        
        if content_type:
            request.content_type = content_type
        
        # 上传
        self.client.put_object(request)
        
        # 返回访问URL
        return self.get_url(key)
    
    async def upload_from_file(self, key: str, file_path: str, content_type: Optional[str] = None) -> str:
        """
        从文件上传到OSS
        
        Args:
            key: 对象键
            file_path: 本地文件路径
            content_type: 内容类型
            
        Returns:
            对象的URL
        """
        full_key = self._get_full_key(key)
        
        # 构建上传请求
        request = models.PutObjectRequest(
            bucket=self.bucket_name,
            key=full_key,
        )
        
        if content_type:
            request.content_type = content_type
        
        # 使用上传管理器上传文件
        uploader = self.client.uploader()
        result = uploader.upload_file(request, file_path)
        
        if result.status_code != 200:
            raise Exception(f"上传失败: {result.status_code} - {result.body}")
        
        # 返回访问URL
        return self.get_url(key)
    
    async def download(self, key: str) -> bytes:
        """
        从OSS下载数据
        
        Args:
            key: 对象键
            
        Returns:
            下载的数据
        """
        full_key = self._get_full_key(key)
        
        # 构建下载请求
        request = models.GetObjectRequest(
            bucket=self.bucket_name,
            key=full_key,
        )
        
        # 下载
        result = self.client.get_object(request)
        
        if result.status_code != 200:
            raise Exception(f"下载失败: {result.status_code} - {result.body}")
        
        # 读取数据
        data = b""
        for chunk in result.body.iter_bytes():
            data += chunk
        
        return data
    
    async def download_to_file(self, key: str, file_path: str) -> None:
        """
        从OSS下载到本地文件
        
        Args:
            key: 对象键
            file_path: 本地文件路径
        """
        full_key = self._get_full_key(key)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 构建下载请求
        request = models.GetObjectRequest(
            bucket=self.bucket_name,
            key=full_key,
        )
        
        # 使用下载管理器下载文件
        downloader = self.client.downloader()
        result = downloader.download_file(request, file_path)
        
        if result.status_code != 200:
            raise Exception(f"下载失败: {result.status_code} - {result.body}")
    
    async def delete(self, key: str) -> bool:
        """
        从OSS删除对象
        
        Args:
            key: 对象键
            
        Returns:
            是否删除成功
        """
        full_key = self._get_full_key(key)
        
        try:
            # 构建删除请求
            request = models.DeleteObjectRequest(
                bucket=self.bucket_name,
                key=full_key,
            )
            
            # 删除
            result = self.client.delete_object(request)
            
            return result.status_code == 204
        except Exception as e:
            print(f"删除OSS对象失败: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查对象是否存在
        
        Args:
            key: 对象键
            
        Returns:
            对象是否存在
        """
        full_key = self._get_full_key(key)
        
        try:
            # 使用is_object_exist方法
            return self.client.is_object_exist(
                bucket=self.bucket_name,
                key=full_key,
            )
        except Exception:
            return False
    
    def get_url(self, key: str) -> str:
        """
        获取对象的访问URL
        
        Args:
            key: 对象键
            
        Returns:
            对象的URL
        """
        full_key = self._get_full_key(key)
        
        # 如果指定了自定义endpoint，使用它
        if self.endpoint and not self.endpoint.endswith("aliyuncs.com"):
            # 检查endpoint是否已有协议前缀
            if self.endpoint.startswith("http://") or self.endpoint.startswith("https://"):
                return f"{self.endpoint}/{self.bucket_name}/{full_key}"
            # 如果没有协议前缀，根据use_ssl添加
            protocol = "https://" if self.use_ssl else "http://"
            return f"{protocol}{self.endpoint}/{self.bucket_name}/{full_key}"
        
        # 否则根据region构造标准endpoint
        # 标准格式: http://<bucket>.oss-<region>.aliyuncs.com/<key> 或 https://...
        if not self.endpoint.startswith("http://") or not self.endpoint.startswith("https://"):
            protocol = "https://" if self.use_ssl else "http://"
        return f"{protocol}{self.bucket_name}.oss-{self.region}.aliyuncs.com/{full_key}"
    
    async def test_connection(self) -> bool:
        """
        测试OSS连接
        
        Returns:
            连接是否正常
        """
        try:
            # 尝试判断bucket是否存在
            bucket_exists = self.client.is_bucket_exist(
                bucket=self.bucket_name,
            )
            return bucket_exists
        except Exception as e:
            print(f"OSS连接测试失败: {e}")
            return False
    
    async def get_usage(self) -> Dict[str, Any]:
        """
        获取存储使用情况（OSS不直接提供，返回估算值）
        
        Returns:
            使用情况字典
        """
        try:
            # 列举所有对象来计算总大小
            paginator = self.client.list_objects_paginator()
            
            total_size = 0
            file_count = 0
            
            for page in paginator.iter_page(models.ListObjectsRequest(
                bucket=self.bucket_name,
            )):
                if page.contents:
                    file_count += len(page.contents)
                    for obj in page.contents:
                        total_size += obj.size
            
            return {
                "used_capacity": total_size,
                "file_count": file_count,
                "available": True,
            }
        except Exception as e:
            print(f"获取OSS使用情况失败: {e}")
            return {
                "used_capacity": 0,
                "file_count": 0,
                "available": False,
            }
    
    async def list_files(self, prefix: Optional[str] = None, max_keys: int = 1000) -> list:
        """
        列出OSS中的文件
        
        Args:
            prefix: 路径前缀
            max_keys: 最大返回数量
            
        Returns:
            文件列表
        """
        full_prefix = None
        if prefix:
            full_prefix = self._get_full_key(prefix)
        
        try:
            # 列举对象
            result = self.client.list_objects(models.ListObjectsRequest(
                bucket=self.bucket_name,
                prefix=full_prefix,
                max_keys=max_keys,
            ))
            
            if result.status_code == 200 and result.contents:
                # 过滤掉前缀，只返回相对路径
                files = []
                for obj in result.contents:
                    # 移除前缀部分
                    obj_key = obj.key
                    if self.prefix and obj_key.startswith(self.prefix + "/"):
                        obj_key = obj_key[len(self.prefix) + 1:]
                    files.append({
                        "key": obj_key,
                        "size": obj.size,
                        "last_modified": obj.last_modified,
                    })
                return files
            
            return []
        except Exception as e:
            print(f"列举OSS文件失败: {e}")
            return []
