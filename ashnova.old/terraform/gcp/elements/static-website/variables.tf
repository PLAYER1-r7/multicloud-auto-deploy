variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for resources"
  type        = string
  default     = "asia-northeast1" # Tokyo
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
  description = "Enable Cloud CDN with Load Balancer"
  type        = bool
  default     = true
}

variable "bucket_location" {
  description = "Bucket location (ASIA for multi-region, asia-northeast1 for single region)"
  type        = string
  default     = "ASIA"
}

variable "custom_domain" {
  description = "Custom domain name for Load Balancer (e.g., www.gcp.ashnova.jp)"
  type        = string
  default     = "www.gcp.ashnova.jp"
}

variable "custom_domains" {
  description = "Custom domain names for Load Balancer (e.g., [\"www.gcp.ashnova.jp\"])"
  type        = list(string)
  default     = []
}

variable "backend_type" {
  description = "Backend type: bucket or cloudrun"
  type        = string
  default     = "bucket"
}

variable "default_host" {
  description = "Default host for routing (e.g., www.gcp.ashnova.jp)"
  type        = string
  default     = ""
}

variable "cloudrun_images" {
  description = "Cloud Run images keyed by host"
  type        = map(string)
  default     = {}
}

variable "cloudrun_service_account_email" {
  description = "Service account email for Cloud Run services (empty to auto-create)"
  type        = string
  default     = ""
}

variable "create_cloudrun_service_account" {
  description = "Whether to create a dedicated service account for Cloud Run services"
  type        = bool
  default     = true
}

variable "host_backend_bucket_map" {
  description = "Map of host to backend bucket name for host-based routing"
  type        = map(string)
  default     = {}
}

variable "labels" {
  description = "Common labels for all resources"
  type        = map(string)
  default = {
    project     = "ashnova"
    managed-by  = "opentofu"
    environment = "production"
  }
}
