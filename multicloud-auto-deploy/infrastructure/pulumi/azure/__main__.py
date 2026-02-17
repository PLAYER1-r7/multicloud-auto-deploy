"""
Multi-Cloud Auto Deploy - Azure Pulumi Implementation

Architecture:
- Azure Functions (Consumption Plan Y1)
- Storage Account (Functions + Frontend)
- Application Insights (Monitoring)

Cost: ~$2-8/month for low traffic
"""

import pulumi
import pulumi_azure_native as azure
import pulumi_azuread as azuread
import pulumi_random as random

# Configuration
config = pulumi.Config()
azure_config = pulumi.Config("azure-native")
location = azure_config.get("location") or "japaneast"
stack = pulumi.get_stack()
project_name = "multicloud-auto-deploy"

# Common tags
common_tags = {
    "Project": project_name,
    "ManagedBy": "pulumi",
    "Environment": stack,
}

# ========================================
# Resource Group
# ========================================
resource_group = azure.resources.ResourceGroup(
    "resource-group",
    resource_group_name=f"{project_name}-{stack}-rg",
    location=location,
    tags=common_tags,
)

# ========================================
# Random suffix for storage accounts (must be globally unique)
# ========================================
storage_suffix = random.RandomString(
    "storage-suffix",
    length=6,
    special=False,
    upper=False,
)

# Random UUID for OAuth2 permission scope
oauth2_scope_id = random.RandomUuid("oauth2-scope-id")

# ========================================
# Storage Account for Azure Functions
# ========================================
functions_storage = azure.storage.StorageAccount(
    "functions-storage",
    account_name=storage_suffix.result.apply(lambda suffix: f"mcadfunc{suffix}"),
    resource_group_name=resource_group.name,
    location=location,
    sku=azure.storage.SkuArgs(
        name="Standard_LRS",  # Locally redundant storage
    ),
    kind="StorageV2",
    minimum_tls_version="TLS1_2",
    tags=common_tags,
)

# ========================================
# Storage Account for Frontend (Static Website)
# ========================================
frontend_storage = azure.storage.StorageAccount(
    "frontend-storage",
    account_name=storage_suffix.result.apply(lambda suffix: f"mcadweb{suffix}"),
    resource_group_name=resource_group.name,
    location=location,
    sku=azure.storage.SkuArgs(
        name="Standard_LRS",
    ),
    kind="StorageV2",
    minimum_tls_version="TLS1_2",
    tags=common_tags,
)

# Enable static website hosting on frontend storage
# Note: This requires using Azure CLI or REST API in the workflow
# Pulumi doesn't directly support static website configuration yet

# ========================================
# Application Insights
# ========================================
app_insights = azure.insights.Component(
    "app-insights",
    resource_group_name=resource_group.name,
    location=location,
    application_type="web",
    kind="web",
    ingestion_mode="ApplicationInsights",  # Use ApplicationInsights instead of LogAnalytics
    tags=common_tags,
)

# ========================================
# Azure Key Vault for Secret Management
# ========================================
# Get current Azure client configuration for tenant ID
current = azure.authorization.get_client_config()

key_vault = azure.keyvault.Vault(
    "key-vault",
    vault_name=storage_suffix.result.apply(lambda suffix: f"mcad-kv-{suffix}"),
    resource_group_name=resource_group.name,
    location=location,
    properties=azure.keyvault.VaultPropertiesArgs(
        tenant_id=current.tenant_id,
        sku=azure.keyvault.SkuArgs(
            family="A",
            name="standard",
        ),
        enable_rbac_authorization=True,  # Use RBAC instead of access policies
        enable_soft_delete=True,
        soft_delete_retention_in_days=7,
        enabled_for_deployment=False,
        enabled_for_disk_encryption=False,
        enabled_for_template_deployment=True,
        network_acls=azure.keyvault.NetworkRuleSetArgs(
            bypass="AzureServices",
            default_action="Allow",  # Change to "Deny" for production with specific IP rules
        ),
    ),
    tags=common_tags,
)

# Store example secret (should be updated with actual values)
app_secret = azure.keyvault.Secret(
    "app-secret",
    secret_name="app-config",
    resource_group_name=resource_group.name,
    vault_name=key_vault.name,
    properties=azure.keyvault.SecretPropertiesArgs(
        value=pulumi.Output.secret('{"database_url":"changeme","api_key":"changeme"}'),
    ),
    tags=common_tags,
)

# ========================================
# Authentication Setup - Azure AD Application
# ========================================
# Azure AD Application for authentication (automated)
# This creates an Azure AD app registration for the API

# Get Azure AD tenant from azuread config
azuread_config = pulumi.Config("azuread")
azure_tenant_id = azuread_config.get("tenantId") or pulumi.Output.from_input("")

# Create Azure AD Application
app_registration = azuread.Application(
    "api-app",
    display_name=f"{project_name}-{stack}-api",
    # Sign-in audience: AzureADMyOrg = Single tenant
    sign_in_audience="AzureADMyOrg",
    # Web application configuration
    web=azuread.ApplicationWebArgs(
        redirect_uris=[
            # Add your frontend URLs here
            f"https://{project_name}-{stack}-web.azurewebsites.net/callback",
            "http://localhost:3000/callback",  # Local development
            "https://localhost:3000/callback",
        ],
        implicit_grant=azuread.ApplicationWebImplicitGrantArgs(
            access_token_issuance_enabled=True,
            id_token_issuance_enabled=True,
        ),
    ),
    # API configuration (expose an API)
    api=azuread.ApplicationApiArgs(
        # OAuth2 permission scopes
        oauth2_permission_scopes=[
            azuread.ApplicationApiOauth2PermissionScopeArgs(
                admin_consent_description="Allow the application to access the API on behalf of the signed-in user.",
                admin_consent_display_name="Access API",
                enabled=True,
                id=oauth2_scope_id.result,
                type="User",
                user_consent_description="Allow the application to access the API on your behalf.",
                user_consent_display_name="Access API",
                value="API.Access",
            ),
        ],
    ),
    opts=pulumi.ResourceOptions(depends_on=[resource_group]),
)

# Create Service Principal for the application
app_service_principal = azuread.ServicePrincipal(
    "api-sp",
    client_id=app_registration.client_id,
    app_role_assignment_required=False,
    opts=pulumi.ResourceOptions(depends_on=[app_registration]),
)

# ========================================
# Note: Function App is managed manually
# ========================================
# Function App and App Service Plan are created and managed manually
# Existing resources:
# - Function App: multicloud-auto-deploy-staging-func
# - App Service Plan: FC1 (FlexConsumption)
# - API URL: https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net

# ========================================
# Azure Front Door for Frontend CDN
# ========================================
# Front Door Profile (Standard SKU - cost-effective)
frontdoor_profile = azure.cdn.Profile(
    "frontdoor-profile",
    profile_name=f"{project_name}-{stack}-fd",
    resource_group_name=resource_group.name,
    location="Global",  # Front Door is global
    sku=azure.cdn.SkuArgs(
        name="Standard_AzureFrontDoor",
    ),
    tags=common_tags,
    # Force replacement when SKU changes (Premium -> Standard not supported)
    opts=pulumi.ResourceOptions(replace_on_changes=["sku"]),
)

# Front Door Endpoint
frontdoor_endpoint = azure.cdn.AFDEndpoint(
    "frontdoor-endpoint",
    endpoint_name=storage_suffix.result.apply(lambda suffix: f"mcad-{stack}-{suffix}"),
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
    location="Global",
    enabled_state="Enabled",
    tags=common_tags,
)

# Front Door Origin Group
frontdoor_origin_group = azure.cdn.AFDOriginGroup(
    "frontdoor-origin-group",
    origin_group_name=f"{project_name}-{stack}-origin-group",
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
    load_balancing_settings=azure.cdn.LoadBalancingSettingsParametersArgs(
        sample_size=4,
        successful_samples_required=3,
        additional_latency_in_milliseconds=50,
    ),
    health_probe_settings=azure.cdn.HealthProbeParametersArgs(
        probe_path="/",
        probe_request_type="HEAD",
        probe_protocol="Https",
        probe_interval_in_seconds=100,
    ),
)

# Front Door Origin (Storage Account for Frontend)
frontdoor_origin = azure.cdn.AFDOrigin(
    "frontdoor-origin",
    origin_name=f"{project_name}-{stack}-origin",
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
    origin_group_name=frontdoor_origin_group.name,
    host_name=frontend_storage.primary_endpoints.apply(
        lambda endpoints: (
            endpoints.web.replace("https://", "").replace("/", "")
            if endpoints.web
            else ""
        )
    ),
    origin_host_header=frontend_storage.primary_endpoints.apply(
        lambda endpoints: (
            endpoints.web.replace("https://", "").replace("/", "")
            if endpoints.web
            else ""
        )
    ),
    http_port=80,
    https_port=443,
    priority=1,
    weight=1000,
    enabled_state="Enabled",
)

# Front Door Route
frontdoor_route = azure.cdn.Route(
    "frontdoor-route",
    route_name=f"{project_name}-{stack}-route",
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
    endpoint_name=frontdoor_endpoint.name,
    origin_group=azure.cdn.ResourceReferenceArgs(
        id=frontdoor_origin_group.id,
    ),
    supported_protocols=["Http", "Https"],
    patterns_to_match=["/*"],
    forwarding_protocol="HttpsOnly",
    link_to_default_domain="Enabled",
    https_redirect="Enabled",
    opts=pulumi.ResourceOptions(depends_on=[frontdoor_origin]),
)

# ========================================
# Outputs
# ========================================
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("functions_storage_name", functions_storage.name)
pulumi.export("frontend_storage_name", frontend_storage.name)

# Azure AD Authentication
pulumi.export("azure_ad_client_id", app_registration.client_id)
pulumi.export("azure_ad_object_id", app_registration.id)  # Object ID of the application
pulumi.export(
    "auth_config_instructions",
    pulumi.Output.concat(
        "Configure Function App with these environment variables:\\n",
        "  AUTH_PROVIDER=azure\\n",
        "  AZURE_TENANT_ID=<your-tenant-id>\\n",
        "  AZURE_CLIENT_ID=", app_registration.client_id, "\\n",
    )
)

# Existing manually-managed Function App
pulumi.export("function_app_name", f"{project_name}-{stack}-func")
pulumi.export(
    "api_url",
    "https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net",
)

pulumi.export(
    "frontend_url",
    frontend_storage.primary_endpoints.apply(
        lambda endpoints: endpoints.web if endpoints.web else "Not configured yet"
    ),
)
pulumi.export("frontdoor_endpoint_name", frontdoor_endpoint.name)
pulumi.export("frontdoor_hostname", frontdoor_endpoint.host_name)
pulumi.export(
    "frontdoor_url",
    frontdoor_endpoint.host_name.apply(lambda hostname: f"https://{hostname}"),
)
pulumi.export("app_insights_instrumentation_key", app_insights.instrumentation_key)
pulumi.export("key_vault_name", key_vault.name)
pulumi.export("key_vault_uri", key_vault.properties.vault_uri)

# Cost estimation
pulumi.export(
    "cost_estimate",
    "Azure Functions FlexConsumption: Pay-as-you-go. "
    "Storage: $0.02/GB/month. "
    "Application Insights: 5GB free/month. "
    "Azure Front Door Standard: $35/month + $0.01/GB. "
    "Key Vault: $0.03 per 10,000 operations (secrets are free). "
    "Estimated: $35-50/month with Front Door Standard.",
)
