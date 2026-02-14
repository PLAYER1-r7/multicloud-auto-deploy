"""バックエンド取得ユーティリティ"""
from functools import lru_cache

from app.config import settings, CloudProvider
from app.backends import BaseBackend
from app.backends.local import LocalBackend


@lru_cache()
def get_backend() -> BaseBackend:
    """設定に基づいてバックエンドを取得"""
    if settings.cloud_provider == CloudProvider.LOCAL:
        return LocalBackend()

    elif settings.cloud_provider == CloudProvider.AWS:
        from app.backends.aws import AWSBackend

        # Use region from settings, or let boto3 auto-detect (e.g., from AWS_REGION in Lambda)
        return AWSBackend(
            table_name=settings.dynamodb_table_name,
            region=settings.aws_region if settings.aws_region else None,
        )

    elif settings.cloud_provider == CloudProvider.AZURE:
        # TODO: Azure Cosmos DB実装
        raise NotImplementedError("Azure backend not yet implemented")

    elif settings.cloud_provider == CloudProvider.GCP:
        # TODO: GCP Firestore実装
        raise NotImplementedError("GCP backend not yet implemented")

    else:
        raise ValueError(f"Unknown cloud provider: {settings.cloud_provider}")
