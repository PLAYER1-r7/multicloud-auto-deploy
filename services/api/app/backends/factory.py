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
        from app.backends.azure import AzureBackend

        if not settings.azure_cosmos_endpoint or not settings.azure_cosmos_key:
            raise ValueError(
                "Azure Cosmos DB credentials not configured. "
                "Set AZURE_COSMOS_ENDPOINT and AZURE_COSMOS_KEY environment variables."
            )

        return AzureBackend(
            endpoint=settings.azure_cosmos_endpoint,
            key=settings.azure_cosmos_key,
        )

    elif settings.cloud_provider == CloudProvider.GCP:
        from app.backends.gcp import GCPBackend

        if not settings.gcp_project_id:
            raise ValueError(
                "GCP project ID not configured. Set GCP_PROJECT_ID environment variable."
            )

        return GCPBackend(
            project_id=settings.gcp_project_id,
            collection_name=settings.firestore_collection,
        )

    else:
        raise ValueError(f"Unknown cloud provider: {settings.cloud_provider}")
