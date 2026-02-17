module "simple_sns" {
  count  = var.enable_simple_sns ? 1 : 0
  source = "../../elements/simple-sns"

  gcp_project_id = var.gcp_project_id
  gcp_region     = var.gcp_region
  project_name   = var.simple_sns_project_name
  environment    = var.simple_sns_environment
  labels         = var.simple_sns_labels

  bucket_name_suffix             = var.simple_sns_bucket_name_suffix
  bucket_name_suffix_length      = var.simple_sns_bucket_name_suffix_length
  frontend_public                = var.simple_sns_frontend_public
  functions_zip_path             = var.simple_sns_functions_zip_path
  allowed_origins                = var.simple_sns_allowed_origins
  include_gcs_origin             = var.simple_sns_include_gcs_origin
  include_frontend_bucket_origin = var.simple_sns_include_frontend_bucket_origin
  functions_runtime              = var.simple_sns_functions_runtime
  functions_timeout_seconds      = var.simple_sns_functions_timeout_seconds
  functions_min_instance_count   = var.simple_sns_functions_min_instance_count
  functions_max_instance_count   = var.simple_sns_functions_max_instance_count
}

locals {
  static_site_host_backend_bucket_map = length(var.static_site_host_backend_bucket_map) > 0 ? var.static_site_host_backend_bucket_map : (
    var.enable_simple_sns && var.static_site_sns_host != "" ? {
      (var.static_site_sns_host) = module.simple_sns[0].frontend_bucket
    } : {}
  )
}

module "static_website" {
  count  = var.enable_static_site ? 1 : 0
  source = "../../elements/static-website"

  gcp_project_id                  = var.gcp_project_id
  gcp_region                      = var.gcp_region
  project_name                    = var.static_site_project_name
  environment                     = var.static_site_environment
  enable_cdn                      = var.static_site_enable_cdn
  bucket_location                 = var.static_site_bucket_location
  custom_domain                   = var.static_site_custom_domain
  custom_domains                  = var.static_site_custom_domains
  backend_type                    = var.static_site_backend_type
  default_host                    = var.static_site_default_host
  cloudrun_images                 = var.static_site_cloudrun_images
  cloudrun_service_account_email  = var.static_site_cloudrun_service_account_email
  create_cloudrun_service_account = var.static_site_create_cloudrun_service_account
  host_backend_bucket_map         = local.static_site_host_backend_bucket_map
  labels                          = var.static_site_labels
}
