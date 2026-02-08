variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = null
}

variable "azure_subscription_id" {
  description = "Azure subscription ID (optional, uses default if not set)"
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

variable "enable_cdn" {
  description = "Enable Azure CDN"
  type        = bool
  default     = null
}

variable "enable_https" {
  description = "Enable HTTPS with CDN (requires custom domain)"
  type        = bool
  default     = null
}

variable "custom_domain" {
  description = "Custom domain name for CDN (e.g., www.azure.ashnova.jp)"
  type        = string
  default     = null
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default     = null
}
