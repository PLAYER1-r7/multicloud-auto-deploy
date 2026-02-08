variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
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

variable "simple_sns_labels" {
  description = "Labels for Simple-SNS"
  type        = map(string)
  default     = {}
}

variable "simple_sns_bucket_name_suffix" {
  description = "Optional fixed suffix for Simple-SNS bucket names"
  type        = string
  default     = null
}

variable "simple_sns_bucket_name_suffix_length" {
  description = "Random suffix length for Simple-SNS buckets"
  type        = number
  default     = 6
}

variable "simple_sns_frontend_public" {
  description = "Make Simple-SNS frontend bucket publicly readable"
  type        = bool
  default     = true
}

variable "simple_sns_functions_zip_path" {
  description = "Path to Simple-SNS functions.zip"
  type        = string
  default     = ""

  validation {
    condition     = var.enable_simple_sns == false || length(var.simple_sns_functions_zip_path) > 0
    error_message = "simple_sns_functions_zip_path is required when enable_simple_sns is true."
  }
}

variable "simple_sns_allowed_origins" {
  description = "Allowed CORS origins for Simple-SNS"
  type        = list(string)
  default     = []
}

variable "simple_sns_include_gcs_origin" {
  description = "Include storage.googleapis.com in CORS origins"
  type        = bool
  default     = true
}

variable "simple_sns_include_frontend_bucket_origin" {
  description = "Include frontend bucket origin in CORS origins"
  type        = bool
  default     = true
}

variable "simple_sns_functions_runtime" {
  description = "Runtime for Simple-SNS Cloud Functions"
  type        = string
  default     = "nodejs22"
}

variable "simple_sns_functions_timeout_seconds" {
  description = "Timeout seconds for Simple-SNS Cloud Functions"
  type        = number
  default     = 60
}

variable "simple_sns_functions_min_instance_count" {
  description = "Min instance count for Simple-SNS Cloud Functions"
  type        = number
  default     = 0
}

variable "simple_sns_functions_max_instance_count" {
  description = "Max instance count for Simple-SNS Cloud Functions"
  type        = number
  default     = 100
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
  description = "Enable Cloud CDN"
  type        = bool
}

variable "static_site_bucket_location" {
  description = "Bucket location"
  type        = string
}

variable "static_site_custom_domain" {
  description = "Custom domain for static website"
  type        = string
}

variable "static_site_custom_domains" {
  description = "Custom domains for static website"
  type        = list(string)
  default     = []
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
  default     = ""
}

variable "static_site_create_cloudrun_service_account" {
  description = "Whether to create a dedicated Cloud Run service account"
  type        = bool
  default     = true
}

variable "static_site_sns_host" {
  description = "Host for Simple-SNS frontend routing (e.g., sns.gcp.ashnova.jp)"
  type        = string
  default     = ""
}

variable "static_site_host_backend_bucket_map" {
  description = "Host to backend bucket name map for static website"
  type        = map(string)
  default     = {}
}

variable "static_site_labels" {
  description = "Labels for static website"
  type        = map(string)
  default     = {}
}
