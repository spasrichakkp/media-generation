"""S3/MinIO storage adapter using async boto3 client."""

import logging
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


class S3Storage:
    """
    Async S3/MinIO storage adapter.
    
    Provides file storage functionality using AWS S3 or MinIO (S3-compatible).
    Supports upload, download, delete, and presigned URL generation.
    
    Example:
        ```python
        storage = S3Storage(
            endpoint_url="http://localhost:9000",  # MinIO
            access_key_id="minioadmin",
            secret_access_key="minioadmin",
            bucket_name="media-generation",
            region="us-east-1",
            use_ssl=False
        )
        
        # Upload file
        await storage.upload("path/to/file.jpg", b"file content")
        
        # Download file
        content = await storage.download("path/to/file.jpg")
        
        # Get presigned URL
        url = await storage.get_presigned_url("path/to/file.jpg", expires_in=3600)
        ```
    """
    
    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        bucket_name: str,
        region: str = "us-east-1",
        endpoint_url: Optional[str] = None,
        use_ssl: bool = True,
    ) -> None:
        """
        Initialize S3/MinIO storage adapter.
        
        Args:
            access_key_id: AWS access key ID or MinIO access key
            secret_access_key: AWS secret access key or MinIO secret key
            bucket_name: S3 bucket name
            region: AWS region (default: us-east-1)
            endpoint_url: Custom endpoint URL (for MinIO, e.g., "http://localhost:9000")
            use_ssl: Whether to use SSL/TLS (default: True for AWS, False for local MinIO)
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url
        self.use_ssl = use_ssl
        
        # Session (initialized in connect())
        self._session: Optional[aioboto3.Session] = None
    
    def _get_session(self) -> aioboto3.Session:
        """
        Get or create aioboto3 session.
        
        Returns:
            aioboto3 Session instance
        """
        if self._session is None:
            self._session = aioboto3.Session(
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region,
            )
        return self._session
    
    async def upload(
        self,
        key: str,
        data: Union[bytes, BytesIO],
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Upload file to S3/MinIO.
        
        Args:
            key: Object key (path) in the bucket
            data: File content as bytes or BytesIO
            content_type: MIME type of the file (e.g., "image/jpeg")
            metadata: Optional metadata dictionary
            
        Returns:
            True if upload successful, False otherwise
        """
        session = self._get_session()
        
        try:
            async with session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3_client:
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type
                if metadata:
                    extra_args["Metadata"] = metadata
                
                # Convert bytes to BytesIO if needed
                if isinstance(data, bytes):
                    data = BytesIO(data)
                
                await s3_client.upload_fileobj(
                    data,
                    self.bucket_name,
                    key,
                    ExtraArgs=extra_args if extra_args else None,
                )
                
                logger.info(f"Uploaded file to S3: {key}")
                return True
                
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error uploading file to S3 '{key}': {e}")
            return False
    
    async def download(self, key: str) -> Optional[bytes]:
        """
        Download file from S3/MinIO.
        
        Args:
            key: Object key (path) in the bucket
            
        Returns:
            File content as bytes, or None if not found
        """
        session = self._get_session()
        
        try:
            async with session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3_client:
                buffer = BytesIO()
                await s3_client.download_fileobj(
                    self.bucket_name,
                    key,
                    buffer,
                )
                
                logger.info(f"Downloaded file from S3: {key}")
                return buffer.getvalue()
                
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.warning(f"File not found in S3: {key}")
            else:
                logger.error(f"Error downloading file from S3 '{key}': {e}")
            return None
        except BotoCoreError as e:
            logger.error(f"Error downloading file from S3 '{key}': {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """
        Delete file from S3/MinIO.
        
        Args:
            key: Object key (path) in the bucket
            
        Returns:
            True if deletion successful, False otherwise
        """
        session = self._get_session()
        
        try:
            async with session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3_client:
                await s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                
                logger.info(f"Deleted file from S3: {key}")
                return True
                
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error deleting file from S3 '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if file exists in S3/MinIO.
        
        Args:
            key: Object key (path) in the bucket
            
        Returns:
            True if file exists, False otherwise
        """
        session = self._get_session()
        
        try:
            async with session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3_client:
                await s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=key,
                )
                return True
                
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Error checking file existence in S3 '{key}': {e}")
            return False
        except BotoCoreError as e:
            logger.error(f"Error checking file existence in S3 '{key}': {e}")
            return False
    
    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        http_method: str = "GET",
    ) -> Optional[str]:
        """
        Generate presigned URL for temporary access to file.
        
        Args:
            key: Object key (path) in the bucket
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)
            http_method: HTTP method for the URL (GET or PUT)
            
        Returns:
            Presigned URL string, or None on error
        """
        session = self._get_session()
        
        try:
            async with session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3_client:
                client_method = "get_object" if http_method == "GET" else "put_object"
                
                url = await s3_client.generate_presigned_url(
                    ClientMethod=client_method,
                    Params={
                        "Bucket": self.bucket_name,
                        "Key": key,
                    },
                    ExpiresIn=expires_in,
                )
                
                return url
                
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error generating presigned URL for '{key}': {e}")
            return None
    
    async def list_objects(
        self,
        prefix: str = "",
        max_keys: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        List objects in bucket with optional prefix filter.
        
        Args:
            prefix: Key prefix to filter by (e.g., "images/")
            max_keys: Maximum number of objects to return
            
        Returns:
            List of object metadata dictionaries
        """
        session = self._get_session()
        
        try:
            async with session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3_client:
                response = await s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    Prefix=prefix,
                    MaxKeys=max_keys,
                )
                
                objects = response.get("Contents", [])
                return [
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                        "etag": obj["ETag"],
                    }
                    for obj in objects
                ]
                
        except (BotoCoreError, ClientError) as e:
            logger.error(f"Error listing objects in S3 with prefix '{prefix}': {e}")
            return []
    
    async def health_check(self) -> bool:
        """
        Check if S3/MinIO connection is healthy.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        session = self._get_session()
        
        try:
            async with session.client(
                "s3",
                endpoint_url=self.endpoint_url,
                use_ssl=self.use_ssl,
            ) as s3_client:
                # Try to head the bucket
                await s3_client.head_bucket(Bucket=self.bucket_name)
                return True
                
        except (BotoCoreError, ClientError):
            return False

