from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings

from app.models import CloudProvider


class Settings(BaseSettings):
    """アプリケーション設定 (v1.2.2)"""

    # クラウドプロバイダー
    cloud_provider: CloudProvider = CloudProvider.LOCAL

    # 認証設定
    auth_disabled: bool = False
    auth_provider: str | None = None
    auth_issuer: str | None = None
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    admin_group: str = "Admins"

    # ローカル開発設定 (DynamoDB Local + MinIO)
    dynamodb_endpoint: str | None = Field(default="http://localhost:8001")
    dynamodb_table_name: str = Field(default="simple-sns-local")
    minio_endpoint: str | None = None
    minio_access_key: str | None = None
    minio_secret_key: str | None = None
    # Accepts both MINIO_BUCKET and MINIO_BUCKET_NAME environment variables
    minio_bucket: str = Field(
        default="images",
        validation_alias=AliasChoices("minio_bucket", "minio_bucket_name"),
    )
    # Public URL for browser-side PUT requests (falls back to minio_endpoint)
    minio_public_endpoint: str | None = None

    # AWS設定
    aws_region: str = "ap-northeast-1"
    textract_region: str = "ap-northeast-2"
    bedrock_region: str = "us-east-1"
    posts_table_name: str | None = None
    images_bucket_name: str | None = None
    images_cdn_url: str | None = None
    bedrock_model_id: str = "amazon.nova-pro-v1:0"
    solve_allow_remote_image_url: bool = True
    solve_max_image_bytes: int = 5 * 1024 * 1024
    solve_ocr_review_min_score: float = 0.35
    solve_ocr_review_max_replacement_ratio: float = 0.01
    # Accepts both COGNITO_USER_POOL_ID and AWS_COGNITO_USER_POOL_ID
    cognito_user_pool_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "cognito_user_pool_id", "aws_cognito_user_pool_id"
        ),
    )
    # Accepts both COGNITO_CLIENT_ID and AWS_COGNITO_CLIENT_ID
    cognito_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("cognito_client_id", "aws_cognito_client_id"),
    )

    # Azure設定
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_storage_account_name: str | None = None
    azure_storage_account_key: str | None = None
    azure_storage_container: str = "images"

    # Cosmos DB設定
    # NOTE: AZURE_COSMOS_DATABASE/CONTAINER names are reserved by Azure CLI/Function App
    #       and always return null values. Use COSMOS_DB_* prefix instead.
    #       Both naming conventions are supported via AliasChoices for compatibility.
    cosmos_db_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("cosmos_db_endpoint", "azure_cosmos_endpoint"),
    )
    cosmos_db_key: str | None = Field(
        default=None, validation_alias=AliasChoices("cosmos_db_key", "azure_cosmos_key")
    )
    cosmos_db_database: str = Field(
        default="simple-sns",
        validation_alias=AliasChoices("cosmos_db_database", "azure_cosmos_database"),
    )
    cosmos_db_container: str = Field(
        default="items",
        validation_alias=AliasChoices("cosmos_db_container", "azure_cosmos_container"),
    )

    # GCP設定
    gcp_project_id: str | None = None
    gcp_client_id: str | None = None
    gcp_service_account: str | None = None
    gcp_storage_bucket: str | None = None
    gcp_posts_collection: str = "posts"
    gcp_profiles_collection: str = "profiles"

    # 共通設定
    presigned_url_expiry: int = 300
    cors_origins: str = "*"
    log_level: str = "INFO"
    # 画像アップロード制限 (環境変数 MAX_IMAGES_PER_POST で上書き可)
    max_images_per_post: int = 10

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


# シングルトンインスタンス
settings = Settings()
