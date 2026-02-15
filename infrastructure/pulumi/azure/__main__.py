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
# Front Door Profile
frontdoor_profile = azure.cdn.Profile(
    "frontdoor-profile",
    profile_name=f"{project_name}-{stack}-fd",
    resource_group_name=resource_group.name,
    location="Global",  # Front Door is global
    sku=azure.cdn.SkuArgs(
        name="Standard_AzureFrontDoor",
    ),
    tags=common_tags,
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

# Cost estimation
pulumi.export(
    "cost_estimate",
    "Azure Functions FlexConsumption: Pay-as-you-go. "
    "Storage: $0.02/GB/month. "
    "Application Insights: 5GB free/month. "
    "Azure Front Door Standard: $35/month + $0.01/GB. "
    "Estimated: $35-50/month with Front Door.",
)
