terraform {
  required_version = ">= 1.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }

  backend "gcs" {
    bucket = "multicloud-auto-deploy-tfstate-gcp"
    prefix = "terraform/state"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# Variables
variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "asia-northeast1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "staging"
}

# Local values
locals {
  resource_prefix = "mcad-${var.environment}"
  common_labels = {
    environment = var.environment
    project     = "multicloud-auto-deploy"
    managed_by  = "terraform"
  }
}

# Storage bucket for function source code
resource "google_storage_bucket" "function_source" {
  name     = "${var.project_id}-${var.environment}-function-source"
  location = var.region
  labels   = local.common_labels

  uniform_bucket_level_access = true
}

# Storage bucket for frontend (static website)
resource "google_storage_bucket" "frontend" {
  name     = "${var.project_id}-${var.environment}-frontend"
  location = var.region
  labels   = local.common_labels

  website {
    main_page_suffix = "index.html"
    not_found_page   = "index.html"
  }

  uniform_bucket_level_access = true
}

# Make frontend bucket public
resource "google_storage_bucket_iam_member" "frontend_public" {
  bucket = google_storage_bucket.frontend.name
  role   = "roles/storage.objectViewer"
  member = "allUsers"
}

# Cloud Functions (Gen 2) - これがCloud Runベースの最新版
resource "google_cloudfunctions2_function" "api" {
  name     = "${local.resource_prefix}-api"
  location = var.region

  build_config {
    runtime     = "python311"
    entry_point = "handler" # function.py の関数名
    source {
      storage_source {
        bucket = google_storage_bucket.function_source.name
        object = "function-source.zip" # これは後でアップロード
      }
    }
  }

  service_config {
    max_instance_count               = 10
    min_instance_count               = 0
    available_memory                 = "512M"
    timeout_seconds                  = 60
    max_instance_request_concurrency = 1
    available_cpu                    = "1"

    environment_variables = {
      ENVIRONMENT = var.environment
    }

    ingress_settings               = "ALLOW_ALL"
    all_traffic_on_latest_revision = true
  }

  labels = local.common_labels
}

# Cloud Functions Invoker permission (public access)
resource "google_cloudfunctions2_function_iam_member" "invoker" {
  project        = google_cloudfunctions2_function.api.project
  location       = google_cloudfunctions2_function.api.location
  cloud_function = google_cloudfunctions2_function.api.name
  role           = "roles/cloudfunctions.invoker"
  member         = "allUsers"
}

# Outputs
output "function_name" {
  description = "Cloud Function name"
  value       = google_cloudfunctions2_function.api.name
}

output "function_uri" {
  description = "Cloud Function URI"
  value       = google_cloudfunctions2_function.api.service_config[0].uri
}

output "api_url" {
  description = "API URL"
  value       = google_cloudfunctions2_function.api.service_config[0].uri
}

output "frontend_storage_bucket" {
  description = "Frontend storage bucket name"
  value       = google_storage_bucket.frontend.name
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "https://storage.googleapis.com/${google_storage_bucket.frontend.name}/index.html"
}

output "function_source_bucket" {
  description = "Function source storage bucket"
  value       = google_storage_bucket.function_source.name
}
