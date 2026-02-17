variable "azure_location" {
  description = "Azure region for resources"
  type        = string
  default     = "japaneast" # 東日本
}

variable "azure_subscription_id" {
  description = "Azure subscription ID (optional, uses default if not set)"
  type        = string
  default     = "29031d24-d41a-4f97-8362-46b40129a7e8"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ashnova"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "enable_cdn" {
  description = "Enable Azure CDN"
  type        = bool
  default     = true
}

variable "enable_https" {
  description = "Enable HTTPS with CDN (requires custom domain)"
  type        = bool
  default     = false
}

variable "custom_domain" {
  description = "Custom domain name for CDN (e.g., www.azure.ashnova.jp)"
  type        = string
  default     = "www.azure.ashnova.jp"
}

variable "tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Project     = "ashnova"
    ManagedBy   = "OpenTofu"
    Environment = "production"
  }
}
