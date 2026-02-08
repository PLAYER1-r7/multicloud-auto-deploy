variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = "29031d24-d41a-4f97-8362-46b40129a7e8"
}

variable "azure_location" {
  description = "Azure region for resources"
  type        = string

  default = "japaneast"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "simple-sns"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "prod"
}

variable "custom_domain" {
  description = "Custom domain name (e.g., sns.azure.ashnova.jp)"
  type        = string
  default     = "sns.azure.ashnova.jp"
}

variable "additional_custom_domain" {
  description = "Additional custom domain name (e.g., www.azure.ashnova.jp). Leave empty to skip."
  type        = string
  default     = ""
}

variable "existing_function_app_name" {
  description = "Existing Azure Function App name to use"
  type        = string
  default     = "simple-sns-func-test"
}

variable "enable_function_app_management" {
  description = "Whether to manage the existing Function App and related settings"
  type        = bool
  default     = true
}

variable "function_app_service_plan_name" {
  description = "Service Plan name for the existing Function App"
  type        = string
  default     = "JapanEastLinuxDynamicPlan"
}

variable "enable_application_insights" {
  description = "Whether to manage Application Insights for the Function App"
  type        = bool
  default     = true
}

variable "static_web_origin" {
  description = "Static website origin (e.g., https://<account>.z11.web.core.windows.net). Leave empty to skip."
  type        = string
  default     = ""
}

variable "azure_ad_tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
  default     = "a3182bec-d835-4ce3-af06-04579abf597e"
}

variable "azure_ad_client_id" {
  description = "Azure AD application (client) ID"
  type        = string
  default     = "00433640-13d1-4482-aa1b-db5f039197bf"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "ashnova-simple-sns"
    ManagedBy   = "OpenTofu"
    Environment = "production"
    Platform    = "Azure"
  }
}
