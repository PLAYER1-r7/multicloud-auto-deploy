module "config" {
  source = "../../config"
}

data "terraform_remote_state" "simple_sns" {
  backend = "local"

  config = {
    path = "${path.root}/../simple-sns/terraform.tfstate"
  }
}

locals {
  gcp_project_id  = coalesce(var.gcp_project_id, module.config.gcp_project_id)
  gcp_region      = coalesce(var.gcp_region, module.config.gcp_region)
  project_name    = coalesce(var.project_name, module.config.static_site_project_name)
  environment     = coalesce(var.environment, module.config.static_site_environment)
  enable_cdn      = var.enable_cdn != null ? var.enable_cdn : module.config.static_site_enable_cdn
  bucket_location = coalesce(var.bucket_location, module.config.static_site_bucket_location)
  custom_domain   = coalesce(var.custom_domain, module.config.static_site_custom_domain)
  custom_domains  = local.custom_domain != "" ? [local.custom_domain, "sns.gcp.ashnova.jp"] : ["sns.gcp.ashnova.jp"]
  labels          = var.labels != null ? var.labels : module.config.static_site_labels

  simple_sns_project_name = module.config.simple_sns_project_name
  simple_sns_environment  = module.config.simple_sns_environment
  simple_sns_labels       = module.config.simple_sns_labels

  simple_sns_frontend_bucket = try(data.terraform_remote_state.simple_sns.outputs.frontend_bucket, "")
}

module "static_website" {
  source = "../../modules/merged"

  enable_simple_sns  = false
  enable_static_site = true

  gcp_project_id = local.gcp_project_id
  gcp_region     = local.gcp_region

  simple_sns_project_name = local.simple_sns_project_name
  simple_sns_environment  = local.simple_sns_environment
  simple_sns_labels       = local.simple_sns_labels

  static_site_project_name    = local.project_name
  static_site_environment     = local.environment
  static_site_enable_cdn      = local.enable_cdn
  static_site_bucket_location = local.bucket_location
  static_site_custom_domain   = local.custom_domain
  static_site_custom_domains  = local.custom_domains
  static_site_host_backend_bucket_map = local.simple_sns_frontend_bucket != "" ? {
    "sns.gcp.ashnova.jp" = local.simple_sns_frontend_bucket
  } : {}
  static_site_labels = local.labels
}
