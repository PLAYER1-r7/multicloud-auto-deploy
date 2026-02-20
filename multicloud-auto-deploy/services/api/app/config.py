from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

from app.models import CloudProvider


class Settings(BaseSettings):
    """アプリケーション設定 (v1.2.2)"""

    # クラウドプロバイダー
    cloud_provider: CloudProvider = CloudProvider.LOCAL

    # 認証設定
    auth_disabled: bool = False
    auth_provider: Optional[str] = None
    auth_issuer: Optional[str] = None
    auth_jwks_url: Optional[str] = None
    auth_audience: Optional[str] = None
    admin_group: str = "Admins"

    # ローカル開発設定 (DynamoDB Local + MinIO)
    dynamodb_endpoint: Optional[str] = Field(default="http://localhost:8001")
    dynamodb_table_name: str = Field(default="simple-sns-local")
    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    # Accepts both MINIO_BUCKET and MINIO_BUCKET_NAME environment variables
    minio_bucket: str = Field(
        default="images",
        validation_alias=AliasChoices("minio_bucket", "minio_bucket_name"),
    )
    # Public URL for browser-side PUT requests (falls back to minio_endpoint)
    minio_public_endpoint: Optional[str] = None

    # AWS設定
    aws_region: str = "ap-northeast-1"
    posts_table_name: Optional[str] = None
    images_bucket_name: Optional[str] = None
    images_cdn_url: Optional[str] = None
    cognito_user_pool_id: Optional[str] = None
    cognito_client_id: Optional[str] = None

    # Azure設定
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_storage_account_name: Optional[str] = None
    azure_storage_account_key: Optional[str] = None
    azure_storage_container: str = "images"

    # Cosmos DB設定
    # NOTE: AZURE_COSMOS_DATABASE/CONTAINER names are reserved by Azure CLI/Function App
    #       and always return null values. Use COSMOS_DB_* prefix instead.
    #       Both naming conventions are supported via AliasChoices for compatibility.
    cosmos_db_endpoint: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "cosmos_db_endpoint", "azure_cosmos_endpoint")
    )
    cosmos_db_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("cosmos_db_key", "azure_cosmos_key")
    )
    cosmos_db_database: str = Field(
        default="simple-sns",
        validation_alias=AliasChoices(
            "cosmos_db_database", "azure_cosmos_database")
    )
    cosmos_db_container: str = Field(
        default="items",
        validation_alias=AliasChoices(
            "cosmos_db_container", "azure_cosmos_container")
    )

    # GCP設定
    gcp_project_id: Optional[str] = None
    gcp_client_id: Optional[str] = None
    gcp_service_account: Optional[str] = None
    gcp_storage_bucket: Optional[str] = None
    gcp_posts_collection: str = "posts"
    gcp_profiles_collection: str = "profiles"

    # 共通設定
    presigned_url_expiry: int = 300
    cors_origins: str = "*"
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


# シングルトンインスタンス
settings = Settings()
