variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
  default     = null
}

variable "gcp_region" {
  description = "GCP region for resources"
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
  description = "Enable Cloud CDN with Load Balancer"
  type        = bool
  default     = null
}

variable "bucket_location" {
  description = "Bucket location (ASIA for multi-region, asia-northeast1 for single region)"
  type        = string
  default     = null
}

variable "custom_domain" {
  description = "Custom domain name for Load Balancer (e.g., www.gcp.ashnova.jp)"
  type        = string
  default     = null
}

variable "labels" {
  description = "Common labels for all resources"
  type        = map(string)
  default     = null
}
