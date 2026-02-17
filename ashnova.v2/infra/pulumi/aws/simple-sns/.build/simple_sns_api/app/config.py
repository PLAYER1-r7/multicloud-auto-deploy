from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cloud_provider: str = "aws"
    auth_provider: str | None = None

    # AWS
    aws_region: str = "ap-northeast-1"
    posts_table_name: str | None = None
    images_bucket_name: str | None = None
    images_cdn_url: str | None = None
    cognito_user_pool_id: str | None = None
    cognito_client_id: str | None = None

    # Azure
    azure_tenant_id: str | None = None
    azure_client_id: str | None = None
    azure_storage_account_name: str | None = None
    azure_storage_account_key: str | None = None
    azure_storage_container: str = "images"
    cosmos_db_endpoint: str | None = None
    cosmos_db_key: str | None = None
    cosmos_db_database: str = "simple-sns"
    cosmos_db_container: str = "items"

    # GCP
    gcp_project_id: str | None = None
    gcp_client_id: str | None = None
    gcp_storage_bucket: str | None = None
    gcp_posts_collection: str = "posts"
    gcp_profiles_collection: str = "profiles"

    # Generic Auth
    auth_issuer: str | None = None
    auth_jwks_url: str | None = None
    auth_audience: str | None = None
    admin_group: str = "Admins"

    # App specific
    presigned_url_expiry: int = 300

    @property
    def effective_auth_provider(self) -> str:
        return self.auth_provider or self.cloud_provider

    model_config = {"env_file": ".env"}


settings = Settings()
