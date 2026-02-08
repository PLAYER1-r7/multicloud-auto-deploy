variable "azure_subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "azure_location" {
  description = "Azure region for resources"
  type        = string
}

variable "enable_simple_sns" {
  description = "Enable Simple-SNS resources"
  type        = bool
  default     = true
}

variable "enable_static_site" {
  description = "Enable static website resources"
  type        = bool
  default     = true
}

variable "simple_sns_project_name" {
  description = "Project name for Simple-SNS"
  type        = string
}

variable "simple_sns_environment" {
  description = "Environment for Simple-SNS"
  type        = string
}

variable "simple_sns_custom_domain" {
  description = "Custom domain for Simple-SNS"
  type        = string
}

variable "simple_sns_additional_custom_domain" {
  description = "Additional custom domain for Simple-SNS"
  type        = string
  default     = ""
}

variable "simple_sns_existing_function_app_name" {
  description = "Existing Function App name"
  type        = string
}

variable "simple_sns_enable_function_app_management" {
  description = "Manage existing Function App"
  type        = bool
}

variable "simple_sns_static_web_origin" {
  description = "Static web origin for CORS"
  type        = string
}

variable "simple_sns_azure_ad_tenant_id" {
  description = "Azure AD tenant ID"
  type        = string
}

variable "simple_sns_azure_ad_client_id" {
  description = "Azure AD client ID"
  type        = string
}

variable "simple_sns_tags" {
  description = "Tags for Simple-SNS"
  type        = map(string)
  default     = {}
}

variable "static_site_project_name" {
  description = "Project name for static website"
  type        = string
}

variable "static_site_environment" {
  description = "Environment for static website"
  type        = string
}

variable "static_site_enable_cdn" {
  description = "Enable Azure CDN"
  type        = bool
}

variable "static_site_enable_https" {
  description = "Enable HTTPS with CDN"
  type        = bool
}

variable "static_site_custom_domain" {
  description = "Custom domain for static website"
  type        = string
}

variable "static_site_tags" {
  description = "Tags for static website"
  type        = map(string)
  default     = {}
}
