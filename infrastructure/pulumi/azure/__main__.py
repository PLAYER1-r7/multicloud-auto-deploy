"""
Multi-Cloud Auto Deploy - Azure Pulumi Implementation

Architecture:
- Azure Functions (Consumption Plan Y1)
- Storage Account (Functions + Frontend)
- Application Insights (Monitoring)

Cost: ~$2-8/month for low traffic
"""

import monitoring
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

# Frontend domain (Azure Front Door hostname) — set after first deploy:
#   pulumi config set frontendDomain <afd_hostname>
# Used for Azure AD app registration redirect URIs
frontend_domain = config.get("frontendDomain") or ""

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
# Log Analytics Workspace (Centralized audit & security logging)
# Azure Front Door (CDN + Custom Domain)
# ========================================
# Production only: Front Door provides CDN and custom domain support
# Staging uses direct Storage Account URL for cost optimization

if stack == "production":
    # Front Door Profile
    front_door_profile = azure.cdn.Profile(
        "front-door-profile",
        profile_name=f"{project_name}-fd",
        resource_group_name=resource_group.name,
        location="global",  # Front Door is a global resource
        sku=azure.cdn.SkuArgs(
            name="Standard_AzureFrontDoor",
        ),
        tags=common_tags,
    )

    # Front Door Endpoint
    front_door_endpoint = azure.cdn.AFDEndpoint(
        "front-door-endpoint",
        resource_group_name=resource_group.name,
        profile_name=front_door_profile.name,
        endpoint_name=f"mcad-{stack}",
        enabled_state="Enabled",
    )

    # Origin Group: Health probes + load balancing configuration
    origin_group = azure.cdn.AFDOriginGroup(
        "origin-group",
        resource_group_name=resource_group.name,
        profile_name=front_door_profile.name,
        origin_group_name="app-origins",
        session_affinity_state="Disabled",
        load_balancing_settings=azure.cdn.LoadBalancingSettingsParametersArgs(
            additional_latency_in_milliseconds=0,
            sample_size=4,
            successful_samples_required=3,
        ),
        health_probe_settings=azure.cdn.HealthProbeParametersArgs(
            probe_protocol="Https",
            probe_request_type="GET",
            probe_path="/",  # Check root for static website
            probe_interval_in_seconds=100,
        ),
    )

    # Origin: Storage Account for static website
    storage_origin = azure.cdn.AFDOrigin(
        "storage-origin",
        resource_group_name=resource_group.name,
        profile_name=front_door_profile.name,
        origin_group_name=origin_group.name,
        origin_name="static-site",
        enabled_state="Enabled",
        host_name=frontend_storage.primary_endpoints.apply(
            lambda endpoints: endpoints.web.replace("https://", "").replace("/", "")
        ),
        http_port=80,
        https_port=443,
        origin_host_header=frontend_storage.primary_endpoints.apply(
            lambda endpoints: endpoints.web.replace("https://", "").replace("/", "")
        ),
        enforce_certificate_name_check=True,
        priority=1,  # Priority for load balancing (1-5, 1 is highest)
        weight=1000,  # Weight for load balancing (1-1000)
    )

    # Custom Domain: www.azure.ashnova.jp
    custom_domain = azure.cdn.AFDCustomDomain(
        "custom-domain",
        resource_group_name=resource_group.name,
        profile_name=front_door_profile.name,
        custom_domain_name="www-azure-ashnova",
        host_name="www.azure.ashnova.jp",
        tls_settings=azure.cdn.AFDDomainHttpsParametersArgs(
            certificate_type="ManagedCertificate",
            minimum_tls_version="TLS12",
        ),
    )

    # Routing Rule: Forward all traffic to origin group
    routing_rule = azure.cdn.Route(
        "catch-all-route",
        resource_group_name=resource_group.name,
        profile_name=front_door_profile.name,
        endpoint_name=front_door_endpoint.name,
        route_name="all-traffic",
        origin_group=azure.cdn.ResourceReferenceArgs(id=origin_group.id),
        patterns_to_match=["/*"],
        enabled_state="Enabled",
        https_redirect="Enabled",
        forwarding_protocol="HttpsOnly",
        link_to_default_domain="Enabled",
        supported_protocols=["Http", "Https"],
        custom_domains=[
            azure.cdn.ActivatedResourceReferenceArgs(id=custom_domain.id),
        ],
        cache_configuration=azure.cdn.AfdRouteCacheConfigurationArgs(
            query_string_caching_behavior="UseQueryString",  # Match Pulumi existing state
            compression_settings=azure.cdn.CompressionSettingsArgs(
                is_compression_enabled=True,
                content_types_to_compress=[
                    "text/html",
                    "text/css",
                    "application/javascript",
                    "application/json",
                ],
            ),
        ),
    )

else:
    # Staging environment: Direct Storage Account URL (no Front Door)
    front_door_profile = None
    front_door_endpoint = None

# ========================================
# Log Analytics Workspace (Centralized audit & security logging)
# ========================================
# Workspace for aggregating logs from Front Door, Function App, Cosmos DB, and Azure AD
log_analytics_workspace = azure.operationalinsights.Workspace(
    "log-analytics-workspace",
    workspace_name=storage_suffix.result.apply(lambda suffix: f"mcad-logs-{suffix}"),
    resource_group_name=resource_group.name,
    location=location,
    sku=azure.operationalinsights.WorkspaceSkuArgs(
        name="PerGB2018",  # Pay-per-GB (5 GB/month free tier)
    ),
    retention_in_days=30,  # Retain logs for 30 days
    tags=common_tags,
)

# ========================================
# Application Insights
# ========================================
app_insights = azure.insights.Component(
    "app-insights",
    resource_group_name=resource_group.name,
    location=location,
    application_type="web",
    kind="web",
    # Send telemetry to Log Analytics Workspace for centralized visibility
    ingestion_mode="LogAnalytics",
    workspace_resource_id=log_analytics_workspace.id,
    tags=common_tags,
)

# ========================================
# Cosmos DB for NoSQL Database
# ========================================
cosmos_account = azure.documentdb.DatabaseAccount(
    "cosmos-account",
    account_name=storage_suffix.result.apply(lambda suffix: f"mcad-cosmos-{suffix}"),
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
            included_paths=[azure.documentdb.IncludedPathArgs(path="/*")],
            excluded_paths=[azure.documentdb.ExcludedPathArgs(path='/"_etag"/?')],
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
            # Legacy / fallback
            f"https://{project_name}-{stack}-web.azurewebsites.net/callback",
            # Note: FrontDoor not deployed in staging (cost optimization)
            # Production may use Front Door with additional URIs
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
# Function Apps (Flex Consumption Plan)
# ========================================
# Two separate Function Apps for SNS API and Exam Solver API
# Flex Consumption Plan: Auto-scaling, pay-per-execution

# App Service Plan (Consumption) for both Function Apps
app_service_plan = azure.web.AppServicePlan(
    "app-service-plan",
    resource_group_name=resource_group.name,
    location=location,
    kind="FunctionApp",
    sku=azure.web.SkuDescriptionArgs(
        name="Y1",  # Consumption Plan (Dynamic)
        tier="Dynamic",
    ),
    tags=common_tags,
)

# SNS API Function App
sns_function_app = azure.web.WebApp(
    "sns-function-app",
    resource_group_name=resource_group.name,
    location=location,
    server_farm_id=app_service_plan.id,
    kind="FunctionApp",
    identity=azure.web.ManagedServiceIdentityArgs(type="SystemAssigned"),
    https_only=True,
    site_config=azure.web.SiteConfigArgs(
        python_version="3.13",
        app_settings=[
            azure.web.NameValuePairArgs(
                name="AzureWebJobsStorage",
                value=pulumi.Output.concat(
                    "DefaultEndpointsProtocol=https;AccountName=",
                    functions_storage.name,
                    ";AccountKey=",
                    functions_storage.primary_endpoints.apply(lambda _: "placeholder"),
                    ";EndpointSuffix=core.windows.net",
                ),
            )
        ],
        cors=azure.web.CorsSettingsArgs(
            allowed_origins=["*"],
        ),
    ),
    tags=common_tags,
)

# Solver API Function App
solver_function_app = azure.web.WebApp(
    "solver-function-app",
    resource_group_name=resource_group.name,
    location=location,
    server_farm_id=app_service_plan.id,
    kind="FunctionApp",
    identity=azure.web.ManagedServiceIdentityArgs(type="SystemAssigned"),
    https_only=True,
    site_config=azure.web.SiteConfigArgs(
        python_version="3.13",
        app_settings=[
            azure.web.NameValuePairArgs(
                name="AzureWebJobsStorage",
                value=pulumi.Output.concat(
                    "DefaultEndpointsProtocol=https;AccountName=",
                    functions_storage.name,
                    ";AccountKey=",
                    functions_storage.primary_endpoints.apply(lambda _: "placeholder"),
                    ";EndpointSuffix=core.windows.net",
                ),
            )
        ],
        cors=azure.web.CorsSettingsArgs(
            allowed_origins=["*"],
        ),
    ),
    tags=common_tags,
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

# Function App IDs for monitoring
sns_function_app_id = sns_function_app.id
solver_function_app_id = solver_function_app.id

# Setup monitoring for both Function Apps
monitoring_resources = monitoring.setup_monitoring(
    project_name=project_name,
    stack=stack,
    resource_group_name=resource_group.name,
    location=location,
    function_app_id=sns_function_app_id,  # SNS API monitoring
    cosmos_account_id=cosmos_account.id,
    alarm_email=alarm_email,
    function_memory_mb=function_memory_mb,
)

# ========================================
# Outputs
# ========================================
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("functions_storage_name", functions_storage.name)
pulumi.export("frontend_storage_name", frontend_storage.name)
# Function Apps
pulumi.export("sns_function_app_name", sns_function_app.name)
pulumi.export(
    "sns_function_app_url",
    sns_function_app.default_host_name.apply(lambda name: f"https://{name}"),
)
pulumi.export("solver_function_app_name", solver_function_app.name)
pulumi.export(
    "solver_function_app_url",
    solver_function_app.default_host_name.apply(lambda name: f"https://{name}"),
)
pulumi.export(
    "api_url", sns_function_app.default_host_name.apply(lambda name: f"https://{name}")
)  # Default to SNS API
# Azure Front Door (production only)
if stack == "production":
    pulumi.export("front_door_profile_name", front_door_profile.name)
    pulumi.export(
        "front_door_host",
        front_door_endpoint.host_name,
    )
    pulumi.export(
        "front_door_custom_domain",
        "www.azure.ashnova.jp",
    )
    pulumi.export(
        "front_door_dns_instructions",
        pulumi.Output.concat(
            "Add CNAME record in Route 53:\\n",
            "  Name: www.azure.ashnova.jp\\n",
            "  Type: CNAME\\n",
            "  Value: ",
            front_door_endpoint.host_name,
            "\\n\\n",
            "After DNS propagates, verify with:\\n",
            "  curl https://www.azure.ashnova.jp/",
        ),
    )
else:
    pulumi.export(
        "front_door_note", "Front Door not deployed in staging (cost optimization)"
    )

# Azure AD Authentication
pulumi.export("azure_ad_client_id", app_registration.client_id)
# Object ID of the application
pulumi.export("azure_ad_object_id", app_registration.id)
pulumi.export(
    "auth_config_instructions",
    pulumi.Output.concat(
        "Configure Function Apps with these environment variables:\\n",
        "  AUTH_PROVIDER=azure\\n",
        "  AZURE_TENANT_ID=<your-tenant-id>\\n",
        "  AZURE_CLIENT_ID=",
        app_registration.client_id,
        "\\n",
    ),
)

pulumi.export(
    "frontend_url",
    frontend_storage.primary_endpoints.apply(
        lambda endpoints: endpoints.web if endpoints.web else "Not configured yet"
    ),
)
pulumi.export("app_insights_instrumentation_key", app_insights.instrumentation_key)
pulumi.export("key_vault_name", key_vault.name)
pulumi.export("key_vault_uri", key_vault.properties.vault_uri)
pulumi.export("log_analytics_workspace_name", log_analytics_workspace.name)
pulumi.export("log_analytics_workspace_id", log_analytics_workspace.id)

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
    pulumi.export("monitoring_action_group_id", monitoring_resources["action_group"].id)
pulumi.export(
    "monitoring_function_alerts",
    list(monitoring_resources["function_alerts"].keys()),
)
pulumi.export(
    "monitoring_cosmos_alerts", list(monitoring_resources["cosmos_alerts"].keys())
)

# Cost estimation
pulumi.export(
    "cost_estimate",
    "Azure Functions FlexConsumption: Pay-as-you-go. "
    "Storage: $0.02/GB/month. "
    "Application Insights: 5GB free/month. "
    "Key Vault: $0.03 per 10,000 operations (secrets are free). "
    "Estimated: $2-8/month for low traffic (Front Door not deployed in staging).",
)
