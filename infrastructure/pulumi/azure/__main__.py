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
    min_tls_version="TLS1_2",
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
    min_tls_version="TLS1_2",
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
    resource_name=f"{project_name}-{stack}-ai",
    resource_group_name=resource_group.name,
    location=location,
    application_type="web",
    kind="web",
    tags=common_tags,
)

# ========================================
# App Service Plan (Consumption Plan)
# ========================================
app_service_plan = azure.web.AppServicePlan(
    "app-service-plan",
    name=f"{project_name}-{stack}-asp",
    resource_group_name=resource_group.name,
    location=location,
    sku=azure.web.SkuDescriptionArgs(
        name="Y1",  # Consumption tier
        tier="Dynamic",
    ),
    kind="FunctionApp",
    reserved=True,  # Linux
    tags=common_tags,
)

# ========================================
# Function App
# ========================================
function_app = azure.web.WebApp(
    "function-app",
    name=f"{project_name}-{stack}-func",
    resource_group_name=resource_group.name,
    location=location,
    server_farm_id=app_service_plan.id,
    kind="FunctionApp",
    
    site_config=azure.web.SiteConfigArgs(
        app_settings=[
            azure.web.NameValuePairArgs(
                name="FUNCTIONS_WORKER_RUNTIME",
                value="python",
            ),
            azure.web.NameValuePairArgs(
                name="FUNCTIONS_EXTENSION_VERSION",
                value="~4",
            ),
            azure.web.NameValuePairArgs(
                name="AzureWebJobsStorage",
                value=pulumi.Output.all(
                    resource_group.name,
                    functions_storage.name
                ).apply(lambda args: f"DefaultEndpointsProtocol=https;AccountName={args[1]};AccountKey=...;EndpointSuffix=core.windows.net"),
            ),
            azure.web.NameValuePairArgs(
                name="APPINSIGHTS_INSTRUMENTATIONKEY",
                value=app_insights.instrumentation_key,
            ),
            azure.web.NameValuePairArgs(
                name="ENVIRONMENT",
                value=stack,
            ),
            azure.web.NameValuePairArgs(
                name="CLOUD_PROVIDER",
                value="azure",
            ),
        ],
        linux_fx_version="Python|3.11",
        cors=azure.web.CorsSettingsArgs(
            allowed_origins=["*"],
            support_credentials=False,
        ),
        use32_bit_worker_process=False,
        http20_enabled=True,
    ),
    
    https_only=True,
    tags=common_tags,
)

# ========================================
# Outputs
# ========================================
pulumi.export("resource_group_name", resource_group.name)
pulumi.export("function_app_name", function_app.name)
pulumi.export("functions_storage_name", functions_storage.name)
pulumi.export("frontend_storage_name", frontend_storage.name)
pulumi.export("api_url", function_app.default_host_name.apply(
    lambda host: f"https://{host}"
))
pulumi.export("frontend_url", frontend_storage.primary_endpoints.apply(
    lambda endpoints: endpoints.web if endpoints.web else "Not configured yet"
))
pulumi.export("app_insights_instrumentation_key", app_insights.instrumentation_key)

# Cost estimation
pulumi.export("cost_estimate",
    "Azure Functions Consumption: First 1M executions/month free, then $0.20 per 1M. "
    "Storage: $0.02/GB/month. "
    "Application Insights: 5GB free/month. "
    "Estimated: $2-8/month for low traffic."
)
