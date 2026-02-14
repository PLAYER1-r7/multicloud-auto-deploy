terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "multicloud-auto-deploy-tfstate-rg"
    storage_account_name = "mcadtfstate7701"
    container_name       = "tfstate"
    key                  = "terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }

  # Service Principal authentication via environment variables
  use_cli  = false
  use_msi  = false
  use_oidc = false
}

# Variables
variable "project_name" {
  description = "Project name"
  type        = string
  default     = "multicloud-auto-deploy"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "japaneast"
}

# Local values
locals {
  resource_prefix = "${var.project_name}-${var.environment}"
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    ManagedBy   = "Terraform"
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${local.resource_prefix}-rg"
  location = var.location
  tags     = local.common_tags
}

# Storage Account for Functions
resource "azurerm_storage_account" "functions" {
  name                     = replace("${var.project_name}${var.environment}func", "-", "")
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  tags = local.common_tags
}

# Storage Account for Frontend (Static Website)
resource "azurerm_storage_account" "frontend" {
  name                     = replace("${var.project_name}${var.environment}web", "-", "")
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"

  static_website {
    index_document     = "index.html"
    error_404_document = "index.html"
  }

  tags = local.common_tags
}

# App Service Plan (Consumption Plan for Functions)
resource "azurerm_service_plan" "functions" {
  name                = "${local.resource_prefix}-asp"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "Y1" # Consumption tier

  tags = local.common_tags
}

# Application Insights
resource "azurerm_application_insights" "main" {
  name                = "${local.resource_prefix}-ai"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  application_type    = "web"

  tags = local.common_tags
}

# Azure Functions App
resource "azurerm_linux_function_app" "api" {
  name                       = "${local.resource_prefix}-api"
  resource_group_name        = azurerm_resource_group.main.name
  location                   = azurerm_resource_group.main.location
  service_plan_id            = azurerm_service_plan.functions.id
  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key

  site_config {
    application_stack {
      python_version = "3.11"
    }

    cors {
      allowed_origins = ["*"]
    }

    # Enable Always On for better performance (requires Basic+ tier)
    # always_on = false  # Not available on Consumption plan
  }

  app_settings = {
    "APPLICATIONINSIGHTS_CONNECTION_STRING" = azurerm_application_insights.main.connection_string
    "FUNCTIONS_WORKER_RUNTIME"              = "python"
    "SCM_DO_BUILD_DURING_DEPLOYMENT"        = "true"
    "ENABLE_ORYX_BUILD"                     = "true"
  }

  https_only = true

  tags = local.common_tags
}

# Outputs
output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "function_app_name" {
  description = "Function App name"
  value       = azurerm_linux_function_app.api.name
}

output "function_app_default_hostname" {
  description = "Function App default hostname"
  value       = azurerm_linux_function_app.api.default_hostname
}

output "api_url" {
  description = "API URL"
  value       = "https://${azurerm_linux_function_app.api.default_hostname}"
}

output "frontend_storage_account" {
  description = "Frontend storage account name"
  value       = azurerm_storage_account.frontend.name
}

output "frontend_url" {
  description = "Frontend URL"
  value       = azurerm_storage_account.frontend.primary_web_endpoint
}
