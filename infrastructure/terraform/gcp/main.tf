terraform {
  required_version = ">= 1.0"
  
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # GCS backend for state persistence across GitHub Actions runs
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
