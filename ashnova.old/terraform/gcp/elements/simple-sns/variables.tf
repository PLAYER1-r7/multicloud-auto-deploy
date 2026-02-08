variable "gcp_project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "gcp_region" {
  description = "GCP region for resources"
  type        = string
  default     = "asia-northeast1"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "simple-sns"
}

variable "environment" {
  description = "Environment (dev/prod)"
  type        = string
  default     = "prod"
}

variable "labels" {
  description = "Resource labels"
  type        = map(string)
  default = {
    project     = "simple-sns"
    environment = "production"
    managed_by  = "terraform"
  }
}

variable "bucket_name_suffix" {
  description = "Optional fixed suffix for bucket names"
  type        = string
  default     = null
}

variable "bucket_name_suffix_length" {
  description = "Random suffix length for bucket names"
  type        = number
  default     = 6
}

variable "frontend_public" {
  description = "Make frontend bucket publicly readable"
  type        = bool
  default     = true
}

variable "functions_zip_path" {
  description = "Path to functions.zip"
  type        = string
}

variable "allowed_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = []
}

variable "include_gcs_origin" {
  description = "Include https://storage.googleapis.com in allowed origins"
  type        = bool
  default     = true
}

variable "include_frontend_bucket_origin" {
  description = "Include frontend bucket origin in allowed origins"
  type        = bool
  default     = true
}

variable "functions_runtime" {
  description = "Cloud Functions runtime"
  type        = string
  default     = "nodejs22"
}

variable "functions_timeout_seconds" {
  description = "Cloud Functions timeout seconds"
  type        = number
  default     = 60
}

variable "functions_min_instance_count" {
  description = "Cloud Functions min instance count"
  type        = number
  default     = 0
}

variable "functions_max_instance_count" {
  description = "Cloud Functions max instance count"
  type        = number
  default     = 100
}
