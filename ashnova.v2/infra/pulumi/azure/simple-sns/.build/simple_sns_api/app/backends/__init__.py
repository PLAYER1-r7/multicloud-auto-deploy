from functools import lru_cache

from app import config
from app.backends.aws_backend import AwsBackend
from app.backends.azure_backend import AzureBackend
from app.backends.gcp_backend import GcpBackend


@lru_cache(maxsize=1)
def get_backend():
    provider = (config.CLOUD_PROVIDER or "aws").lower()
    if provider == "azure":
        return AzureBackend()
    if provider == "gcp":
        return GcpBackend()
    return AwsBackend()
