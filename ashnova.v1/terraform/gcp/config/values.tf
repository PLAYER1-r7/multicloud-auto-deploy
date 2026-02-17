locals {
  gcp_project_id = "ashnova"
  gcp_region     = "asia-northeast1"

  simple_sns_project_name = "simple-sns"
  simple_sns_environment  = "prod"
  simple_sns_labels = {
    project     = "simple-sns"
    environment = "production"
    managed_by  = "terraform"
  }

  static_site_project_name    = "ashnova"
  static_site_environment     = "production"
  static_site_enable_cdn      = true
  static_site_bucket_location = "ASIA"
  static_site_custom_domain   = "www.gcp.ashnova.jp"
  static_site_labels = {
    project     = "ashnova"
    managed-by  = "opentofu"
    environment = "production"
  }
}

output "gcp_project_id" {
  value = local.gcp_project_id
}

output "gcp_region" {
  value = local.gcp_region
}

output "simple_sns_project_name" {
  value = local.simple_sns_project_name
}

output "simple_sns_environment" {
  value = local.simple_sns_environment
}

output "simple_sns_labels" {
  value = local.simple_sns_labels
}

output "static_site_project_name" {
  value = local.static_site_project_name
}

output "static_site_environment" {
  value = local.static_site_environment
}

output "static_site_enable_cdn" {
  value = local.static_site_enable_cdn
}

output "static_site_bucket_location" {
  value = local.static_site_bucket_location
}

output "static_site_custom_domain" {
  value = local.static_site_custom_domain
}

output "static_site_labels" {
  value = local.static_site_labels
}
