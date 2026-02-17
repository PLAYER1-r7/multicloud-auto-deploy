import pulumi
import pulumi_azuread as azuread
import pulumi_azure_native as azure_native
from config import project_name, environment, stack


def create_auth_resources():
    # Create Azure AD Application
    app = azuread.Application(
        f"{project_name}-app",
        display_name=f"{project_name}-{environment}-{stack}",
        sign_in_audience="AzureADMyOrg",  # or AzureADMultipleOrgs
        web=azuread.ApplicationWebArgs(
            # Will need to update this with the API/Web URL once known, or set it after?
            redirect_uris=[],
            implicit_grant=azuread.ApplicationWebImplicitGrantArgs(
                access_token_issuance_enabled=True,
                id_token_issuance_enabled=True,
            ),
        ),
    )

    # Create Service Principal
    sp = azuread.ServicePrincipal(
        f"{project_name}-sp",
        client_id=app.client_id,
    )

    # current_config = pulumi.Config("azure-native")
    # tenant_id = current_config.require("tenantId")

    client_config = azure_native.authorization.get_client_config()
    tenant_id = client_config.tenant_id

    return {
        "app": app,
        "sp": sp,
        "client_id": app.client_id,
        "tenant_id": tenant_id
    }
