"""アプリケーション設定"""
import os
from enum import Enum
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class CloudProvider(str, Enum):
    """クラウドプロバイダー"""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    LOCAL = "local"


class Settings(BaseSettings):
    """アプリケーション設定"""

    # Cloud Provider
    cloud_provider: CloudProvider = CloudProvider.LOCAL

    # CORS
    cors_origins: str = "*"

    # Authentication (Cognito/Azure AD/Firebase)
    auth_disabled: bool = True
    cognito_user_pool_id: Optional[str] = None
    cognito_region: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    firebase_project_id: Optional[str] = None

    # AWS
    aws_region: str = "ap-northeast-1"
    dynamodb_table_name: str = "simple-sns-messages"
    s3_bucket_name: Optional[str] = None

    # Azure
    azure_cosmos_endpoint: Optional[str] = None
    azure_cosmos_key: Optional[str] = None
    azure_storage_account: Optional[str] = None
    azure_storage_key: Optional[str] = None

    # GCP
    gcp_project_id: Optional[str] = None
    firestore_collection: str = "messages"
    gcs_bucket_name: Optional[str] = None

    # Local (MinIO)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "simple-sns"

    # Application
    log_level: str = "INFO"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
