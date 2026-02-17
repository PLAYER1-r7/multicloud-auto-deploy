import pulumi
import pulumi_azure_native as azure_native
from config import resource_group
from storage import create_storage_resources
from compute import create_compute_resources
from auth import create_auth_resources

# 0. Create Auth (Azure AD)
auth = create_auth_resources()

# 1. Create Storage (Cosmos DB, Storage Account, ACR)
storage = create_storage_resources()

# 2. Create Compute (Container Apps)
compute = create_compute_resources(storage, auth)

# 3. Exports
api_url = (
    compute["api_container_app"].latest_revision_fqdn.apply(
        lambda host: f"https://{host}")
    if compute["api_container_app"]
    else None
)

pulumi.export("api_url", api_url)
pulumi.export("azure_client_id", auth["client_id"])
pulumi.export("azure_tenant_id", auth["tenant_id"])
pulumi.export("images_storage_account", storage["images_storage"].name)
pulumi.export("cosmos_account", storage["cosmos_account"].name)
pulumi.export("acr_login_server", storage["registry"].login_server)
pulumi.export("acr_username",  storage["registry"].admin_user_enabled.apply(lambda _:
                                                                            azure_native.containerregistry.list_registry_credentials_output(
                                                                                resource_group_name=resource_group.name,
                                                                                registry_name=storage["registry"].name).username))
pulumi.export("acr_password", storage["registry"].admin_user_enabled.apply(lambda _:
                                                                           azure_native.containerregistry.list_registry_credentials_output(
                                                                               resource_group_name=resource_group.name,
                                                                               registry_name=storage["registry"].name).passwords[0].value))
