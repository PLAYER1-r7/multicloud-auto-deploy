module "config" {
  source = "../../config"
}

locals {
  gcp_project_id = coalesce(var.gcp_project_id, module.config.gcp_project_id)
  gcp_region     = coalesce(var.gcp_region, module.config.gcp_region)
  project_name   = coalesce(var.project_name, module.config.simple_sns_project_name)
  environment    = coalesce(var.environment, module.config.simple_sns_environment)
  labels         = var.labels != null ? var.labels : module.config.simple_sns_labels

  simple_sns_bucket_name_suffix             = var.simple_sns_bucket_name_suffix
  simple_sns_bucket_name_suffix_length      = var.simple_sns_bucket_name_suffix_length != null ? var.simple_sns_bucket_name_suffix_length : 6
  simple_sns_frontend_public                = var.simple_sns_frontend_public != null ? var.simple_sns_frontend_public : true
  simple_sns_functions_zip_path             = var.simple_sns_functions_zip_path != null ? var.simple_sns_functions_zip_path : "${path.root}/../../../../gcp/simple-sns/functions.zip"
  simple_sns_allowed_origins                = var.simple_sns_allowed_origins != null ? var.simple_sns_allowed_origins : []
  simple_sns_include_gcs_origin             = var.simple_sns_include_gcs_origin != null ? var.simple_sns_include_gcs_origin : true
  simple_sns_include_frontend_bucket_origin = var.simple_sns_include_frontend_bucket_origin != null ? var.simple_sns_include_frontend_bucket_origin : true
  simple_sns_functions_runtime              = var.simple_sns_functions_runtime != null ? var.simple_sns_functions_runtime : "nodejs22"
  simple_sns_functions_timeout_seconds      = var.simple_sns_functions_timeout_seconds != null ? var.simple_sns_functions_timeout_seconds : 60
  simple_sns_functions_min_instance_count   = var.simple_sns_functions_min_instance_count != null ? var.simple_sns_functions_min_instance_count : 0
  simple_sns_functions_max_instance_count   = var.simple_sns_functions_max_instance_count != null ? var.simple_sns_functions_max_instance_count : 100

  static_site_project_name                    = module.config.static_site_project_name
  static_site_environment                     = module.config.static_site_environment
  static_site_enable_cdn                      = var.static_site_enable_cdn != null ? var.static_site_enable_cdn : module.config.static_site_enable_cdn
  static_site_bucket_location                 = module.config.static_site_bucket_location
  static_site_custom_domain                   = var.static_site_custom_domain != null ? var.static_site_custom_domain : module.config.static_site_custom_domain
  static_site_custom_domains                  = var.static_site_custom_domains != null ? var.static_site_custom_domains : (local.static_site_custom_domain != "" ? [local.static_site_custom_domain] : [])
  static_site_sns_host                        = var.static_site_sns_host != null ? var.static_site_sns_host : ""
  static_site_labels                          = module.config.static_site_labels
  static_site_cloudrun_service_account_email  = var.static_site_cloudrun_service_account_email != null ? var.static_site_cloudrun_service_account_email : ""
  static_site_create_cloudrun_service_account = var.static_site_create_cloudrun_service_account != null ? var.static_site_create_cloudrun_service_account : true
}

module "simple_sns" {
  source = "../../modules/merged"

  enable_simple_sns  = true
  enable_static_site = true

  gcp_project_id = local.gcp_project_id
  gcp_region     = local.gcp_region

  simple_sns_project_name = local.project_name
  simple_sns_environment  = local.environment
  simple_sns_labels       = local.labels

  simple_sns_bucket_name_suffix             = local.simple_sns_bucket_name_suffix
  simple_sns_bucket_name_suffix_length      = local.simple_sns_bucket_name_suffix_length
  simple_sns_frontend_public                = local.simple_sns_frontend_public
  simple_sns_functions_zip_path             = local.simple_sns_functions_zip_path
  simple_sns_allowed_origins                = local.simple_sns_allowed_origins
  simple_sns_include_gcs_origin             = local.simple_sns_include_gcs_origin
  simple_sns_include_frontend_bucket_origin = local.simple_sns_include_frontend_bucket_origin
  simple_sns_functions_runtime              = local.simple_sns_functions_runtime
  simple_sns_functions_timeout_seconds      = local.simple_sns_functions_timeout_seconds
  simple_sns_functions_min_instance_count   = local.simple_sns_functions_min_instance_count
  simple_sns_functions_max_instance_count   = local.simple_sns_functions_max_instance_count

  static_site_project_name                    = local.static_site_project_name
  static_site_environment                     = local.static_site_environment
  static_site_enable_cdn                      = local.static_site_enable_cdn
  static_site_bucket_location                 = local.static_site_bucket_location
  static_site_custom_domain                   = local.static_site_custom_domain
  static_site_custom_domains                  = local.static_site_custom_domains
  static_site_sns_host                        = local.static_site_sns_host
  static_site_labels                          = local.static_site_labels
  static_site_backend_type                    = var.static_site_backend_type
  static_site_default_host                    = var.static_site_default_host
  static_site_cloudrun_images                 = var.static_site_cloudrun_images
  static_site_cloudrun_service_account_email  = local.static_site_cloudrun_service_account_email
  static_site_create_cloudrun_service_account = local.static_site_create_cloudrun_service_account
}
