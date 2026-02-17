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
  description = "Project name"
  type        = string
  default     = null
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
  default     = null
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default     = null
}

variable "simple_sns_bucket_name_suffix" {
  description = "Optional fixed suffix for Simple-SNS bucket names"
  type        = string
  default     = null
}

variable "simple_sns_bucket_name_suffix_length" {
  description = "Random suffix length for Simple-SNS buckets"
  type        = number
  default     = null
}

variable "simple_sns_frontend_public" {
  description = "Make Simple-SNS frontend bucket publicly readable"
  type        = bool
  default     = null
}

variable "simple_sns_functions_zip_path" {
  description = "Path to Simple-SNS functions.zip"
  type        = string
  default     = null
}

variable "simple_sns_allowed_origins" {
  description = "Allowed CORS origins for Simple-SNS"
  type        = list(string)
  default     = null
}

variable "simple_sns_include_gcs_origin" {
  description = "Include storage.googleapis.com in CORS origins"
  type        = bool
  default     = null
}

variable "simple_sns_include_frontend_bucket_origin" {
  description = "Include frontend bucket origin in CORS origins"
  type        = bool
  default     = null
}

variable "simple_sns_functions_runtime" {
  description = "Runtime for Simple-SNS Cloud Functions"
  type        = string
  default     = null
}

variable "simple_sns_functions_timeout_seconds" {
  description = "Timeout seconds for Simple-SNS Cloud Functions"
  type        = number
  default     = null
}

variable "simple_sns_functions_min_instance_count" {
  description = "Min instance count for Simple-SNS Cloud Functions"
  type        = number
  default     = null
}

variable "simple_sns_functions_max_instance_count" {
  description = "Max instance count for Simple-SNS Cloud Functions"
  type        = number
  default     = null
}

variable "static_site_enable_cdn" {
  description = "Enable Cloud CDN for static site"
  type        = bool
  default     = null
}

variable "static_site_custom_domain" {
  description = "Custom domain for static site (empty to use IP)"
  type        = string
  default     = null
}

variable "static_site_backend_type" {
  description = "Backend type for static website (bucket or cloudrun)"
  type        = string
  default     = "bucket"
}

variable "static_site_default_host" {
  description = "Default host for static website routing"
  type        = string
  default     = ""
}

variable "static_site_cloudrun_images" {
  description = "Cloud Run images keyed by host"
  type        = map(string)
  default     = {}
}

variable "static_site_cloudrun_service_account_email" {
  description = "Service account email for static site Cloud Run services"
  type        = string
  default     = null
}

variable "static_site_create_cloudrun_service_account" {
  description = "Whether to create a dedicated Cloud Run service account"
  type        = bool
  default     = null
}

variable "static_site_custom_domains" {
  description = "Custom domains for static site"
  type        = list(string)
  default     = null
}

variable "static_site_sns_host" {
  description = "Host for Simple-SNS frontend routing"
  type        = string
  default     = null
}
