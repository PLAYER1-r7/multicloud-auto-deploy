from typing import Optional
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
    
    # ローカル開発設定
    database_url: Optional[str] = None
    storage_path: str = "./storage"
    minio_endpoint: Optional[str] = None
    minio_access_key: Optional[str] = None
    minio_secret_key: Optional[str] = None
    minio_bucket: str = "images"
    
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
    cosmos_db_endpoint: Optional[str] = None
    cosmos_db_key: Optional[str] = None
    cosmos_db_database: str = "simple-sns"
    cosmos_db_container: str = "items"
    
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
