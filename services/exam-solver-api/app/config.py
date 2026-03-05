from typing import Optional

from pydantic_settings import BaseSettings

from app.models import CloudProvider


class Settings(BaseSettings):
    """Exam Solver API 設定"""

    # クラウドプロバイダー
    cloud_provider: CloudProvider = CloudProvider.LOCAL

    # Solve エンドポイント有効化（コスト制御）
    solve_enabled: bool = False
    solve_allow_remote_image_url: bool = True
    solve_max_image_bytes: int = 10_000_000  # 10 MB

    # Azure設定
    azure_storage_account_name: Optional[str] = None
    azure_storage_account_key: Optional[str] = None
    azure_storage_container: str = "ocr-debug"

    # Azure Document Intelligence (OCR)
    azure_document_intelligence_endpoint: Optional[str] = None
    azure_document_intelligence_key: Optional[str] = None
    azure_di_timeout: int = 120  # seconds

    # Azure OpenAI (LLM)
    azure_openai_endpoint: Optional[str] = None
    azure_openai_key: Optional[str] = None
    azure_openai_deployment: str = "gpt-4o"
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_timeout: int = 60  # seconds
    azure_openai_max_retries: int = 3

    # GCP設定
    gcp_project_id: Optional[str] = None
    gcp_credentials_path: Optional[str] = None
    gcp_vertex_ai_location: str = "asia-northeast1"
    gcp_vertex_ai_model: str = "gemini-2.0-flash"
    gcp_vision_api_timeout: int = 60  # seconds

    # Learning Material Generation API endpoint
    learning_api_url: Optional[str] = None

    # 共通設定
    cors_origins: str = "*"
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
    }


# シングルトンインスタンス
settings = Settings()
