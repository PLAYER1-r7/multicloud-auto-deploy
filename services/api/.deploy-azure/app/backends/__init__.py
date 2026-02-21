from functools import lru_cache
from app.config import settings
from app.models import CloudProvider
from app.backends.base import BackendBase

# Alias for backward compatibility
BaseBackend = BackendBase


@lru_cache(maxsize=1)
def get_backend():
    """
    設定に基づいて適切なバックエンドを取得

    Returns:
        BackendBase実装のインスタンス
    """
    provider = settings.cloud_provider

    if provider == CloudProvider.LOCAL:
        from app.backends.local_backend import LocalBackend

        return LocalBackend()

    elif provider == CloudProvider.AWS:
        from app.backends.aws_backend import AwsBackend

        return AwsBackend()

    elif provider == CloudProvider.AZURE:
        from app.backends.azure_backend import AzureBackend

        return AzureBackend()

    elif provider == CloudProvider.GCP:
        from app.backends.gcp_backend import GcpBackend

        return GcpBackend()

    else:
        raise ValueError(f"Unsupported cloud provider: {provider}")
