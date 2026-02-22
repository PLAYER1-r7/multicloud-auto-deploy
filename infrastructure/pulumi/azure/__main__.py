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
import monitoring

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
    account_name=storage_suffix.result.apply(
        lambda suffix: f"mcadfunc{suffix}"),
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
    account_name=storage_suffix.result.apply(
        lambda suffix: f"mcadweb{suffix}"),
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
    # Use ApplicationInsights instead of LogAnalytics
    ingestion_mode="ApplicationInsights",
    tags=common_tags,
)

# ========================================
# Cosmos DB for NoSQL Database
# ========================================
cosmos_account = azure.documentdb.DatabaseAccount(
    "cosmos-account",
    account_name=storage_suffix.result.apply(
        lambda suffix: f"mcad-cosmos-{suffix}"),
    resource_group_name=resource_group.name,
    location=location,
    database_account_offer_type="Standard",
    locations=[
        azure.documentdb.LocationArgs(
            location_name=location,
            failover_priority=0,
        )
    ],
    consistency_policy=azure.documentdb.ConsistencyPolicyArgs(
        default_consistency_level="Session",  # Session consistency for balance
        max_interval_in_seconds=5,
        max_staleness_prefix=100,
    ),
    enable_automatic_failover=False,
    capabilities=[
        # Serverless mode for cost efficiency
        azure.documentdb.CapabilityArgs(name="EnableServerless"),
    ],
    tags=common_tags,
)

# Cosmos DB Database
cosmos_database = azure.documentdb.SqlResourceSqlDatabase(
    "cosmos-database",
    database_name="messages",
    resource_group_name=resource_group.name,
    account_name=cosmos_account.name,
    resource=azure.documentdb.SqlDatabaseResourceArgs(
        id="messages",
    ),
    opts=pulumi.ResourceOptions(depends_on=[cosmos_account]),
)

# Cosmos DB Container for messages
cosmos_container = azure.documentdb.SqlResourceSqlContainer(
    "cosmos-container",
    container_name="messages",
    resource_group_name=resource_group.name,
    account_name=cosmos_account.name,
    database_name=cosmos_database.name,
    resource=azure.documentdb.SqlContainerResourceArgs(
        id="messages",
        partition_key=azure.documentdb.ContainerPartitionKeyArgs(
            paths=["/userId"],
            kind="Hash",
        ),
        indexing_policy=azure.documentdb.IndexingPolicyArgs(
            automatic=True,
            indexing_mode="Consistent",
            included_paths=[
                azure.documentdb.IncludedPathArgs(path="/*")
            ],
            excluded_paths=[
                azure.documentdb.ExcludedPathArgs(path='/"_etag"/?')
            ],
        ),
    ),
    opts=pulumi.ResourceOptions(depends_on=[cosmos_database]),
)

# Get Cosmos DB keys
cosmos_keys = pulumi.Output.all(resource_group.name, cosmos_account.name).apply(
    lambda args: azure.documentdb.list_database_account_keys(
        resource_group_name=args[0],
        account_name=args[1],
    )
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
        value=pulumi.Output.secret(
            '{"database_url":"changeme","api_key":"changeme"}'),
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
azure_tenant_id = azuread_config.get(
    "tenantId") or pulumi.Output.from_input("")

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
    # Extend origin response timeout to 60s (default: 30s) to accommodate
    # Python Dynamic Consumption cold starts which can take 10-30+ seconds.
    # Without this, AFD times out during cold start and returns HTTP 502.
    origin_response_timeout_seconds=60,
    tags=common_tags,
    # Force replacement when SKU changes (Premium -> Standard not supported)
    opts=pulumi.ResourceOptions(replace_on_changes=["sku"]),
)

# Front Door Endpoint
frontdoor_endpoint = azure.cdn.AFDEndpoint(
    "frontdoor-endpoint",
    endpoint_name=storage_suffix.result.apply(
        lambda suffix: f"mcad-{stack}-{suffix}"),
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

# ========================================
# Front Door: Rule Set for React SPA URL rewriting
# /sns/<deep-link> → /sns/index.html (SPA client-side routing)
#
# Conditions (all AND'd):
#   1. Path begins with /sns/
#   2. Path does NOT begin with /sns/assets/  (preserve static bundles)
#   3. Path does NOT end with known static file extensions
# Action: URL Rewrite source=/sns/  destination=/sns/index.html
# ========================================
spa_rule_set = azure.cdn.RuleSet(
    "spa-rule-set",
    rule_set_name="SpaRuleSet",
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
)

spa_rewrite_rule = azure.cdn.Rule(
    "spa-rewrite-rule",
    rule_name="SpaRouting",
    rule_set_name=spa_rule_set.name,
    profile_name=frontdoor_profile.name,
    resource_group_name=resource_group.name,
    order=1,
    conditions=[
        # Condition 1: path begins with /sns/
        azure.cdn.DeliveryRuleUrlPathConditionArgs(
            name="UrlPath",
            parameters=azure.cdn.UrlPathMatchConditionParametersArgs(
                type_name="DeliveryRuleUrlPathMatchConditionParameters",
                operator="BeginsWith",
                negate_condition=False,
                match_values=["/sns/"],
                transforms=["Lowercase"],
            ),
        ),
        # Condition 2: NOT /sns/assets/ (Vite bundle output)
        azure.cdn.DeliveryRuleUrlPathConditionArgs(
            name="UrlPath",
            parameters=azure.cdn.UrlPathMatchConditionParametersArgs(
                type_name="DeliveryRuleUrlPathMatchConditionParameters",
                operator="BeginsWith",
                negate_condition=True,
                match_values=["/sns/assets/"],
                transforms=["Lowercase"],
            ),
        ),
        # Condition 3: NOT a static file (has no known extension)
        azure.cdn.DeliveryRuleUrlPathConditionArgs(
            name="UrlPath",
            parameters=azure.cdn.UrlPathMatchConditionParametersArgs(
                type_name="DeliveryRuleUrlPathMatchConditionParameters",
                operator="EndsWith",
                negate_condition=True,
                match_values=[
                    ".html", ".js", ".css", ".png", ".svg",
                    ".ico", ".json", ".woff", ".woff2", ".map",
                    ".txt", ".webp", ".jpg", ".jpeg",
                ],
                transforms=["Lowercase"],
            ),
        ),
    ],
    actions=[
        azure.cdn.UrlRewriteActionArgs(
            name="UrlRewrite",
            parameters=azure.cdn.UrlRewriteActionParametersArgs(
                type_name="DeliveryRuleUrlRewriteActionParameters",
                source_pattern="/sns/",
                destination="/sns/index.html",
                preserve_unmatched_path=False,
            ),
        ),
    ],
    opts=pulumi.ResourceOptions(depends_on=[spa_rule_set]),
)

# Front Door Route (/* → Blob Storage with SPA rule set attached)
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
    rule_sets=[azure.cdn.ResourceReferenceArgs(id=spa_rule_set.id)],
    opts=pulumi.ResourceOptions(depends_on=[frontdoor_origin, spa_rewrite_rule]),
)

# ========================================
# Monitoring and Alerts
# ========================================
alarm_email = config.get("alarmEmail")

# Flex Consumption instanceMemoryMB (512 / 2048 / 4096).
# Must match the value configured on the Function App in Azure Portal.
# Default: 2048MB. Update here (and in Pulumi.[stack].yaml) if changed.
# Bug history: was hardcoded to 800MB in monitoring.py, firing Sev3 alerts
# unconditionally on a 2048MB instance (800MB = only 39% of limit).
function_memory_mb = config.get_int("functionMemoryMb") or 2048

# Note: Function App ID is derived from the manually-managed app
client_config = azure.authorization.get_client_config()
function_app_id = pulumi.Output.concat(
    "/subscriptions/",
    client_config.subscription_id,
    "/resourceGroups/",
    resource_group.name,
    "/providers/Microsoft.Web/sites/",
    f"{project_name}-{stack}-func",
)

monitoring_resources = monitoring.setup_monitoring(
    project_name=project_name,
    stack=stack,
    resource_group_name=resource_group.name,
    location=location,
    function_app_id=function_app_id,
    cosmos_account_id=cosmos_account.id,
    frontdoor_profile_id=frontdoor_profile.id,
    alarm_email=alarm_email,
    function_memory_mb=function_memory_mb,
)

# ========================================
# Outputs
# ========================================
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("functions_storage_name", functions_storage.name)
pulumi.export("frontend_storage_name", frontend_storage.name)

# Azure AD Authentication
pulumi.export("azure_ad_client_id", app_registration.client_id)
# Object ID of the application
pulumi.export("azure_ad_object_id", app_registration.id)
pulumi.export(
    "auth_config_instructions",
    pulumi.Output.concat(
        "Configure Function App with these environment variables:\\n",
        "  AUTH_PROVIDER=azure\\n",
        "  AZURE_TENANT_ID=<your-tenant-id>\\n",
        "  AZURE_CLIENT_ID=",
        app_registration.client_id,
        "\\n",
    ),
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
pulumi.export("app_insights_instrumentation_key",
              app_insights.instrumentation_key)
pulumi.export("key_vault_name", key_vault.name)
pulumi.export("key_vault_uri", key_vault.properties.vault_uri)

# Cosmos DB exports
pulumi.export("cosmos_account_name", cosmos_account.name)
pulumi.export("cosmos_db_endpoint", cosmos_account.document_endpoint)
pulumi.export(
    "cosmos_db_key",
    pulumi.Output.secret(cosmos_keys.apply(lambda k: k.primary_master_key)),
)
pulumi.export("cosmos_database_name", cosmos_database.name)
pulumi.export("cosmos_container_name", cosmos_container.name)
pulumi.export(
    "cosmos_connection_instructions",
    pulumi.Output.concat(
        "Configure Function App with these environment variables:\\n",
        "  COSMOS_DB_ENDPOINT=",
        cosmos_account.document_endpoint,
        "\\n",
        "  COSMOS_DB_KEY=<from-pulumi-output>\\n",
        "  COSMOS_DB_DATABASE=",
        cosmos_database.name,
        "\\n",
        "  COSMOS_DB_CONTAINER=",
        cosmos_container.name,
        "\\n",
    ),
)

# Monitoring exports
if monitoring_resources["action_group"]:
    pulumi.export("monitoring_action_group_id",
                  monitoring_resources["action_group"].id)
pulumi.export(
    "monitoring_function_alerts",
    list(monitoring_resources["function_alerts"].keys()),
)
pulumi.export(
    "monitoring_cosmos_alerts", list(
        monitoring_resources["cosmos_alerts"].keys())
)
pulumi.export(
    "monitoring_frontdoor_alerts", list(
        monitoring_resources["frontdoor_alerts"].keys())
)

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
