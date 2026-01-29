import asyncio
from typing import Optional, Dict, Any
import aioboto3
from botocore.exceptions import ClientError, BotoCoreError

from app.core.storages.base import StorageBase


class S3Storage(StorageBase):
    """AWS S3存储实现（支持兼容S3 API的存储服务，如MinIO、R2等）"""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.endpoint_url = config.get("endpoint_url")  # S3兼容服务端点（如MinIO、R2）
        self.access_key_id = config.get("access_key_id") or config.get("aws_access_key_id")
        self.secret_access_key = config.get("secret_access_key") or config.get("aws_secret_access_key")
        self.region_name = config.get("region_name", "us-east-1")
        self.bucket_name = config.get("bucket_name")
        self.base_path = config.get("base_path", "").rstrip("/")  # 存储路径前缀
        # 支持自定义域名用于生成访问URL（如Cloudflare R2的自定义域名）
        self.custom_domain = config.get("custom_domain") or config.get("cdn_domain")  # 自定义域名（可选）
        self.use_ssl = config.get("use_ssl", True)
        
        # 初始化session
        self.session = None
        self._session_lock = asyncio.Lock()
        
        # 验证配置
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError("S3存储需要配置 access_key_id 和 secret_access_key")
        if not self.bucket_name:
            raise ValueError("S3存储需要配置 bucket_name")
    
    async def _get_session(self):
        """获取或创建boto3 session"""
        async with self._session_lock:
            if self.session is None:
                self.session = aioboto3.Session(
                    aws_access_key_id=self.access_key_id,
                    aws_secret_access_key=self.secret_access_key,
                    region_name=self.region_name
                )
            return self.session
    
    async def _get_client(self):
        """获取S3客户端"""
        session = await self._get_session()
        
        client_config = {}
        if self.endpoint_url:
            client_config["endpoint_url"] = self.endpoint_url
            # 如果是自定义端点（如MinIO），通常不使用SSL或需要特殊配置
            if not self.use_ssl:
                # 这里需要确保endpoint_url使用http://而不是https://
                if self.endpoint_url.startswith("https://"):
                    self.endpoint_url = self.endpoint_url.replace("https://", "http://")
        
        return session.client(
            "s3",
            **client_config,
            verify=self.use_ssl
        )
    
    def _get_full_path(self, file_path: str) -> str:
        """获取完整的存储路径"""
        if self.base_path:
            return f"{self.base_path}/{file_path}"
        return file_path
    
    async def upload(self, file_data: bytes, file_path: str) -> str:
        """上传文件到S3"""
        async with await self._get_client() as s3_client:
            full_path = self._get_full_path(file_path)
            
            try:
                await s3_client.put_object(
                    Bucket=self.bucket_name,
                    Key=full_path,
                    Body=file_data,
                    # 可选：设置访问权限
                    # ACL='public-read'  # 如果需要公开访问
                )
                
                # 返回访问URL
                return await self.get_url(file_path)
            except (ClientError, BotoCoreError) as e:
                raise RuntimeError(f"S3上传失败: {str(e)}")
    
    async def download(self, file_path: str) -> bytes:
        """从S3下载文件"""
        async with await self._get_client() as s3_client:
            full_path = self._get_full_path(file_path)
            
            try:
                response = await s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=full_path
                )
                return await response['Body'].read()
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    raise FileNotFoundError(f"文件不存在: {file_path}")
                raise RuntimeError(f"S3下载失败: {str(e)}")
            except BotoCoreError as e:
                raise RuntimeError(f"S3下载失败: {str(e)}")
    
    async def delete(self, file_path: str) -> bool:
        """删除S3中的文件"""
        async with await self._get_client() as s3_client:
            full_path = self._get_full_path(file_path)
            
            try:
                await s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=full_path
                )
                return True
            except (ClientError, BotoCoreError) as e:
                # 文件不存在也算删除成功
                if isinstance(e, ClientError) and e.response['Error']['Code'] == 'NoSuchKey':
                    return True
                return False
    
    async def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        async with await self._get_client() as s3_client:
            full_path = self._get_full_path(file_path)
            
            try:
                await s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=full_path
                )
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404' or e.response['Error']['Code'] == 'NoSuchKey':
                    return False
                raise RuntimeError(f"S3检查文件失败: {str(e)}")
            except BotoCoreError as e:
                raise RuntimeError(f"S3检查文件失败: {str(e)}")
    
    async def get_url(self, file_path: str) -> str:
        """获取文件访问URL"""
        full_path = self._get_full_path(file_path)
        
        # 如果配置了自定义域名，优先使用自定义域名（用于Cloudflare R2等）
        if self.custom_domain:
            return f"{self.custom_domain.rstrip('/')}/{full_path}"
        
        # 否则根据endpoint生成URL
        if self.endpoint_url:
            # 对于Cloudflare R2等S3兼容服务，endpoint通常是API端点
            # 我们不应该在URL中包含bucket名称，因为endpoint可能已经包含了bucket路径
            # 检查endpoint是否是R2风格（包含cloudflarestorage.com）
            if "cloudflarestorage.com" in self.endpoint_url or "r2.cloudflarestorage.com" in self.endpoint_url:
                # R2的endpoint格式: https://accountid.r2.cloudflarestorage.com/bucket
                # 我们需要去掉bucket部分，只保留基础endpoint
                base_endpoint = self.endpoint_url
                # 如果endpoint包含bucket名称，则移除它
                if f"/{self.bucket_name}" in base_endpoint:
                    base_endpoint = base_endpoint.split(f"/{self.bucket_name}")[0]
                return f"{base_endpoint.rstrip('/')}/{self.bucket_name}/{full_path}"
            else:
                # 标准S3或MinIO格式
                return f"{self.endpoint_url.rstrip('/')}/{self.bucket_name}/{full_path}"
        
        # AWS S3默认URL格式
        return f"https://{self.bucket_name}.s3.{self.region_name}.amazonaws.com/{full_path}"
    
    async def test_connection(self) -> bool:
        """测试S3连接"""
        try:
            async with await self._get_client() as s3_client:
                # 尝试列出bucket，如果成功则连接正常
                await s3_client.head_bucket(Bucket=self.bucket_name)
                return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                # Bucket不存在，尝试创建
                try:
                    await s3_client.create_bucket(Bucket=self.bucket_name)
                    return True
                except Exception:
                    return False
            return False
        except Exception:
            return False
    
    async def get_usage(self) -> dict:
        """获取S3存储使用情况"""
        try:
            async with await self._get_client() as s3_client:
                # 如果设置了base_path，只计算该路径下的文件
                prefix = self.base_path + "/" if self.base_path else ""
                
                total_size = 0
                file_count = 0
                
                paginator = s3_client.get_paginator('list_objects_v2')
                async for page in paginator.paginate(
                    Bucket=self.bucket_name,
                    Prefix=prefix
                ):
                    if 'Contents' in page:
                        for obj in page['Contents']:
                            total_size += obj['Size']
                            file_count += 1
                
                return {
                    "used_capacity": total_size,
                    "file_count": file_count,
                    "available": True,
                    "bucket": self.bucket_name
                }
        except Exception as e:
            # 如果无法获取详细信息，返回基本信息
            return {
                "used_capacity": 0,
                "file_count": 0,
                "available": False,
                "bucket": self.bucket_name,
                "error": str(e)
            }
    
    async def list_files(self, prefix: str = "", max_keys: int = 1000) -> list[Dict[str, Any]]:
        """
        列出存储中的文件
        
        Args:
            prefix: 文件路径前缀
            max_keys: 最大返回数量
            
        Returns:
            文件列表，每个文件包含Key, Size, LastModified等信息
        """
        async with await self._get_client() as s3_client:
            full_prefix = self._get_full_path(prefix)
            
            files = []
            paginator = s3_client.get_paginator('list_objects_v2')
            
            async for page in paginator.paginate(
                Bucket=self.bucket_name,
                Prefix=full_prefix,
                MaxKeys=max_keys
            ):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        files.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'url': await self.get_url(obj['Key'])
                        })
            
            return files
    
    async def copy_file(self, source_path: str, dest_path: str) -> bool:
        """
        复制文件
        
        Args:
            source_path: 源文件路径
            dest_path: 目标文件路径
            
        Returns:
            是否复制成功
        """
        async with await self._get_client() as s3_client:
            source_full = self._get_full_path(source_path)
            dest_full = self._get_full_path(dest_path)
            
            try:
                await s3_client.copy_object(
                    Bucket=self.bucket_name,
                    CopySource={
                        'Bucket': self.bucket_name,
                        'Key': source_full
                    },
                    Key=dest_full
                )
                return True
            except Exception as e:
                raise RuntimeError(f"S3复制文件失败: {str(e)}")
