import hashlib
from pathlib import Path
import pulumi
import pulumi_azure_native as azure_native

config = pulumi.Config()
project_name = config.get("project_name") or "simple-sns"
environment = config.get("environment") or "prod"
location = config.get("azure:location") or "japaneast"
custom_tags = config.get_object("tags") or {}
azure_tenant_id = config.get("azure_tenant_id") or ""
azure_client_id = config.get("azure_client_id") or ""
cosmos_account_suffix = config.get("cosmos_account_suffix") or "sv"

# Auth
auth_provider = config.get("auth_provider") or "azure"
cognito_user_pool_id = config.get("cognito_user_pool_id") or ""
cognito_client_id = config.get("cognito_client_id") or ""
deploy_service = config.get_bool("deploy_service")

base_tags = {
    "Project": project_name,
    "Environment": environment,
    "ManagedBy": "Pulumi",
    **custom_tags,
}

repo_root = Path(__file__).resolve().parents[4]
api_source_dir = repo_root / "services" / "simple_sns_api"

stack = pulumi.get_stack()

resource_group = azure_native.resources.ResourceGroup(
    f"{project_name}-rg",
    resource_group_name=f"rg-{project_name}-{environment}",
    location=location,
    tags=base_tags,
)


def sanitize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def storage_account_name(base: str, env: str, stack: str) -> str:
    seed = f"{base}-{env}-{stack}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]
    raw = f"{sanitize_name(base)}{sanitize_name(env)}{digest}"
    return raw[:24]


def cosmos_account_name(base: str, env: str, stack: str, suffix: str) -> str:
    seed = f"{base}-{env}-{stack}-{suffix}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]
    raw = f"{sanitize_name(base)}{sanitize_name(env)}{sanitize_name(suffix)}{digest}"
    return raw[:44]
