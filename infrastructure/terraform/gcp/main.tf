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

# 注意: Cloud Functions は Terraform では作成しません
# 理由: Terraform が storage_source の ZIP ファイルを参照する前に、
#       ZIP がアップロードされている必要があるため、
#       GitHub Actions ワークフローで gcloud CLI を使用してデプロイします

# Outputs
output "function_source_bucket" {
  description = "Function source storage bucket"
  value       = google_storage_bucket.function_source.name
}

output "frontend_storage_bucket" {
  description = "Frontend storage bucket name"
  value       = google_storage_bucket.frontend.name
}

output "frontend_url" {
  description = "Frontend URL"
  value       = "https://storage.googleapis.com/${google_storage_bucket.frontend.name}/index.html"
}

