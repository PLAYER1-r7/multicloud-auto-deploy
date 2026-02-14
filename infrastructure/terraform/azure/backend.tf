# Log Analytics Workspace for Container Apps
resource "azurerm_log_analytics_workspace" "container_apps" {
  name                = "${local.resource_prefix}-logs"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.common_tags
}

# Container App Environment
resource "azurerm_container_app_environment" "main" {
  name                       = "${local.resource_prefix}-env"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.container_apps.id
  tags                       = local.common_tags
}

# Azure Container Registry
resource "azurerm_container_registry" "main" {
  name                = "mcad${var.environment}acr"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Basic"
  admin_enabled       = true
  tags                = local.common_tags
}

# Container App for API
resource "azurerm_container_app" "api" {
  name                         = "mcad-${var.environment}-api"
  resource_group_name          = azurerm_resource_group.main.name
  container_app_environment_id = azurerm_container_app_environment.main.id
  revision_mode                = "Single"

  template {
    container {
      name   = "api"
      image  = "${azurerm_container_registry.main.login_server}/multicloud-auto-deploy-api:latest"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "CLOUD_PROVIDER"
        value = "azure"
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "COSMOS_ENDPOINT"
        value = azurerm_cosmosdb_account.main.endpoint
      }
      env {
        name        = "COSMOS_KEY"
        value       = azurerm_cosmosdb_account.main.primary_key
        secret_name = "cosmos-key"
      }
      env {
        name  = "COSMOS_DATABASE_NAME"
        value = azurerm_cosmosdb_sql_database.main.name
      }
      env {
        name  = "COSMOS_CONTAINER_NAME"
        value = azurerm_cosmosdb_sql_container.messages.name
      }
      env {
        name  = "WEBSITE_INSTANCE_ID"
        value = "azure-container-app"
      }
    }

    min_replicas = 1
    max_replicas = 1
  }

  secret {
    name  = "cosmos-key"
    value = azurerm_cosmosdb_account.main.primary_key
  }

  registry {
    server               = azurerm_container_registry.main.login_server
    username             = azurerm_container_registry.main.admin_username
    password_secret_name = "registry-password"
  }

  secret {
    name  = "registry-password"
    value = azurerm_container_registry.main.admin_password
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  tags = local.common_tags
}

