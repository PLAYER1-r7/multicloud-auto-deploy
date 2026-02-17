import hashlib
import pulumi
import pulumi_gcp as gcp

config = pulumi.Config()
project_name = config.get("project_name") or "simple-sns"
environment = config.get("environment") or "prod"
region = gcp.config.region or "asia-northeast1"
project = gcp.config.project or config.get("gcp:project")
custom_tags = config.get_object("tags") or {}
client_id = config.get("gcp_client_id") or ""
api_image_override = config.get("api_image") or ""
deploy_service = config.get_bool("deploy_service")

# Auth
auth_provider = config.get("auth_provider") or "gcp"
cognito_user_pool_id = config.get("cognito_user_pool_id") or ""
cognito_client_id = config.get("cognito_client_id") or ""

# Helper Functions


def name_suffix(base_str: str, env: str, st: str) -> str:
    """Generate a short hash suffix."""
    return hashlib.sha1(f"{base_str}-{env}-{st}".encode("utf-8")).hexdigest()[:6]


def resource_name(base_str: str, env: str, st: str, suffix_str: str) -> str:
    """Generate a consistent resource name."""
    return f"{base_str}-{env}-{suffix_str}".lower().replace("_", "-")


stack = pulumi.get_stack()
suffix = name_suffix(project_name, environment, stack)
