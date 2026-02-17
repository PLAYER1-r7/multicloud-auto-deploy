import os


def get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value


def get_env_int(name: str, default: int) -> int:
    value = get_env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


CLOUD_PROVIDER = get_env("CLOUD_PROVIDER", "aws")
AUTH_PROVIDER = get_env("AUTH_PROVIDER") or CLOUD_PROVIDER

POSTS_TABLE_NAME = get_env("POSTS_TABLE_NAME")
IMAGES_BUCKET_NAME = get_env("IMAGES_BUCKET_NAME")
AWS_REGION = get_env("AWS_REGION", "ap-northeast-1")

COGNITO_USER_POOL_ID = get_env("COGNITO_USER_POOL_ID")
COGNITO_CLIENT_ID = get_env("COGNITO_CLIENT_ID")

AZURE_TENANT_ID = get_env("AZURE_TENANT_ID")
AZURE_CLIENT_ID = get_env("AZURE_CLIENT_ID")
AZURE_STORAGE_ACCOUNT_NAME = get_env("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = get_env("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_STORAGE_CONTAINER = get_env("AZURE_STORAGE_CONTAINER", "images")
COSMOS_DB_ENDPOINT = get_env("COSMOS_DB_ENDPOINT")
COSMOS_DB_KEY = get_env("COSMOS_DB_KEY")
COSMOS_DB_DATABASE = get_env("COSMOS_DB_DATABASE", "simple-sns")
COSMOS_DB_CONTAINER = get_env("COSMOS_DB_CONTAINER", "items")

GCP_PROJECT_ID = get_env("GCP_PROJECT_ID")
GCP_CLIENT_ID = get_env("GCP_CLIENT_ID")
GCP_STORAGE_BUCKET = get_env("GCP_STORAGE_BUCKET")
GCP_POSTS_COLLECTION = get_env("GCP_POSTS_COLLECTION", "posts")
GCP_PROFILES_COLLECTION = get_env("GCP_PROFILES_COLLECTION", "profiles")

AUTH_ISSUER = get_env("AUTH_ISSUER")
AUTH_JWKS_URL = get_env("AUTH_JWKS_URL")
AUTH_AUDIENCE = get_env("AUTH_AUDIENCE")
ADMIN_GROUP = get_env("ADMIN_GROUP", "Admins")

SIGNED_URL_EXPIRY = get_env_int("SIGNED_URL_EXPIRY", 3600)
PRESIGNED_URL_EXPIRY = get_env_int("PRESIGNED_URL_EXPIRY", 300)
