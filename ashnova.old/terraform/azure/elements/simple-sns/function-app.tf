# Application Insights
resource "azurerm_application_insights" "simple_sns" {
  count               = var.enable_application_insights ? 1 : 0
  name                = local.app_insights_name
  location            = azurerm_resource_group.simple_sns.location
  resource_group_name = azurerm_resource_group.simple_sns.name
  application_type    = "web"

  tags = var.tags
}

locals {
  app_insights_settings = var.enable_application_insights ? {
    "APPLICATIONINSIGHTS_CONNECTION_STRING"      = azurerm_application_insights.simple_sns[0].connection_string
    "APPINSIGHTS_INSTRUMENTATIONKEY"             = azurerm_application_insights.simple_sns[0].instrumentation_key
    "ApplicationInsightsAgent_EXTENSION_VERSION" = "~3"
  } : {}
  app_insights_connection_string   = var.enable_application_insights ? azurerm_application_insights.simple_sns[0].connection_string : null
  app_insights_instrumentation_key = var.enable_application_insights ? azurerm_application_insights.simple_sns[0].instrumentation_key : null
}

resource "azurerm_service_plan" "simple_sns" {
  count               = var.enable_function_app_management ? 1 : 0
  name                = var.function_app_service_plan_name
  resource_group_name = azurerm_resource_group.simple_sns.name
  location            = azurerm_resource_group.simple_sns.location
  os_type             = "Linux"
  sku_name            = "Y1"

  tags = var.tags
}

# Function App (manage settings on existing app)
resource "azurerm_linux_function_app" "simple_sns" {
  count               = var.enable_function_app_management ? 1 : 0
  name                = var.existing_function_app_name
  resource_group_name = azurerm_resource_group.simple_sns.name
  location            = azurerm_resource_group.simple_sns.location
  service_plan_id     = var.enable_function_app_management ? azurerm_service_plan.simple_sns[0].id : null

  https_only = true

  storage_account_name       = azurerm_storage_account.simple_sns.name
  storage_account_access_key = azurerm_storage_account.simple_sns.primary_access_key

  site_config {
    minimum_tls_version                    = "1.2"
    ftps_state                             = "Disabled"
    application_insights_connection_string = local.app_insights_connection_string
    application_insights_key               = local.app_insights_instrumentation_key

    application_stack {
      node_version = "20"
    }

    cors {
      allowed_origins     = local.frontend_origins
      support_credentials = true
    }

    app_service_logs {
      disk_quota_mb         = 100
      retention_period_days = 3
    }
  }

  app_settings = var.enable_function_app_management ? merge(
    data.azurerm_linux_function_app.existing[0].app_settings,
    local.app_insights_settings,
    {
      "AzureWebJobsStorage"                      = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.simple_sns.name};AccountKey=${azurerm_storage_account.simple_sns.primary_access_key};EndpointSuffix=core.windows.net"
      "WEBSITE_CONTENTAZUREFILECONNECTIONSTRING" = "DefaultEndpointsProtocol=https;AccountName=${azurerm_storage_account.simple_sns.name};AccountKey=${azurerm_storage_account.simple_sns.primary_access_key};EndpointSuffix=core.windows.net"
      "WEBSITE_CONTENTSHARE"                     = replace(lower(var.existing_function_app_name), "-", "")
      "FUNCTIONS_WORKER_RUNTIME"                 = "node"
      "WEBSITE_NODE_DEFAULT_VERSION"             = "~20"
      "COSMOS_DB_ENDPOINT"                       = azurerm_cosmosdb_account.simple_sns.endpoint
      "COSMOS_DB_KEY"                            = azurerm_cosmosdb_account.simple_sns.primary_key
      "COSMOS_DB_DATABASE"                       = azurerm_cosmosdb_sql_database.simple_sns.name
      "COSMOS_DB_CONTAINER"                      = azurerm_cosmosdb_sql_container.posts.name
      "STORAGE_ACCOUNT_NAME"                     = azurerm_storage_account.simple_sns.name
      "STORAGE_ACCOUNT_KEY"                      = azurerm_storage_account.simple_sns.primary_access_key
      "STORAGE_IMAGES_CONTAINER"                 = azurerm_storage_container.images.name
      "AZURE_AD_TENANT_ID"                       = var.azure_ad_tenant_id
      "AZURE_AD_CLIENT_ID"                       = var.azure_ad_client_id
    }
  ) : {}

  tags = var.tags

  lifecycle {
    ignore_changes = [
      storage_account_name,
      storage_account_access_key,
      service_plan_id,
      site_config[0].app_service_logs,
      app_settings["WEBSITE_RUN_FROM_PACKAGE"],
      app_settings["SCM_DO_BUILD_DURING_DEPLOYMENT"],
      app_settings["AzureWebJobsFeatureFlags"],
      app_settings["AzureWebJobsStorage"],
      app_settings["WEBSITE_NODE_DEFAULT_VERSION"],
    ]
  }
}
