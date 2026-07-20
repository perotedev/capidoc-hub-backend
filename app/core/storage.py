from functools import lru_cache

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings

settings = get_settings()


class StorageService:
    """Thin wrapper around boto3's S3 client, compatible with both AWS S3 and MinIO.

    Presigned URL generation is a local signature computation (no network call),
    so it is safe to call synchronously; uploads/deletes go through a threadpool
    to avoid blocking the event loop.
    """

    def __init__(self) -> None:
        self._bucket_name = settings.s3_bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            config=BotoConfig(s3={"addressing_style": "path" if settings.s3_use_path_style else "auto"}),
        )

    async def ensure_bucket_exists(self) -> None:
        def _ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket_name)
            except ClientError:
                self._client.create_bucket(Bucket=self._bucket_name)

        await run_in_threadpool(_ensure)

    async def upload_file(self, key: str, content: bytes, content_type: str) -> None:
        await run_in_threadpool(
            self._client.put_object,
            Bucket=self._bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    async def delete_file(self, key: str) -> None:
        await run_in_threadpool(self._client.delete_object, Bucket=self._bucket_name, Key=key)

    async def download_file(self, key: str) -> bytes:
        def _download() -> bytes:
            response = self._client.get_object(Bucket=self._bucket_name, Key=key)
            return response["Body"].read()

        return await run_in_threadpool(_download)

    def generate_presigned_url(self, key: str, expires_in: int | None = None) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket_name, "Key": key},
            ExpiresIn=expires_in or settings.file_url_expire_seconds,
        )


@lru_cache
def get_storage_service() -> StorageService:
    return StorageService()
