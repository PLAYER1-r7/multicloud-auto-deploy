from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_base_url: str = "https://btghogtp08.execute-api.ap-northeast-1.amazonaws.com/prod"
    auth_provider: Literal["aws", "azure", "gcp", "firebase"] = "aws"
    stage_name: str = ""

    # AWS Cognito
    cognito_domain: str = ""
    cognito_client_id: str = ""
    cognito_redirect_uri: str = ""
    cognito_logout_uri: str = ""

    # Azure AD
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_redirect_uri: str = ""
    azure_logout_uri: str = ""

    # GCP Identity / OIDC
    gcp_client_id: str = ""
    gcp_redirect_uri: str = ""
    gcp_logout_uri: str = ""

    # Firebase
    firebase_api_key: str = ""
    firebase_auth_domain: str = ""
    firebase_project_id: str = ""
    firebase_app_id: str = ""

    oidc_scope: str = "openid email profile"

    model_config = {
        "env_file": ".env",
        "env_ignore_empty": True,
        "extra": "ignore",
    }

    @property
    def clean_api_base_url(self) -> str:
        return self.api_base_url.rstrip("/")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
