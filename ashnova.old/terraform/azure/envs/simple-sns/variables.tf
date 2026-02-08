variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
  default     = null
}

variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = null
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = null
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = null
}

variable "custom_domain" {
  description = "Custom domain name (e.g., sns.azure.ashnova.jp)"
  type        = string
  default     = null
}

variable "additional_custom_domain" {
  description = "Additional custom domain name (e.g., www.azure.ashnova.jp)"
  type        = string
  default     = null
}

variable "existing_function_app_name" {
  description = "Existing Azure Function App name to use"
  type        = string
  default     = null
}

variable "enable_function_app_management" {
  description = "Whether to manage the existing Function App and related settings"
  type        = bool
  default     = null
}

variable "static_web_origin" {
  description = "Static website origin (e.g., https://<account>.z11.web.core.windows.net). Leave empty to skip."
  type        = string
  default     = null
}

variable "azure_ad_tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
  default     = null
}

variable "azure_ad_client_id" {
  description = "Azure AD application (client) ID"
  type        = string
  default     = null
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = null
}
