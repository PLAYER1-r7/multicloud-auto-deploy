module "config" {
  source = "../../config"
}

locals {
  azure_subscription_id          = coalesce(var.azure_subscription_id, module.config.azure_subscription_id)
  azure_location                 = coalesce(var.azure_location, module.config.azure_location)
  project_name                   = coalesce(var.project_name, module.config.simple_sns_project_name)
  environment                    = coalesce(var.environment, module.config.simple_sns_environment)
  custom_domain                  = coalesce(var.custom_domain, module.config.simple_sns_custom_domain)
  additional_custom_domain       = var.additional_custom_domain != null ? var.additional_custom_domain : module.config.simple_sns_additional_custom_domain
  existing_function_app_name     = coalesce(var.existing_function_app_name, module.config.simple_sns_existing_function_app_name)
  enable_function_app_management = var.enable_function_app_management != null ? var.enable_function_app_management : module.config.simple_sns_enable_function_app_management
  static_web_origin              = var.static_web_origin != null && var.static_web_origin != "" ? var.static_web_origin : module.config.simple_sns_static_web_origin
  azure_ad_tenant_id             = coalesce(var.azure_ad_tenant_id, module.config.simple_sns_azure_ad_tenant_id)
  azure_ad_client_id             = coalesce(var.azure_ad_client_id, module.config.simple_sns_azure_ad_client_id)
  tags                           = var.tags != null ? var.tags : module.config.simple_sns_tags

  static_site_project_name  = module.config.static_site_project_name
  static_site_environment   = module.config.static_site_environment
  static_site_enable_cdn    = module.config.static_site_enable_cdn
  static_site_enable_https  = module.config.static_site_enable_https
  static_site_custom_domain = module.config.static_site_custom_domain
  static_site_tags          = module.config.static_site_tags
}

module "simple_sns" {
  source = "../../modules/merged"

  enable_simple_sns  = true
  enable_static_site = true

  azure_subscription_id = local.azure_subscription_id
  azure_location        = local.azure_location

  simple_sns_project_name                   = local.project_name
  simple_sns_environment                    = local.environment
  simple_sns_custom_domain                  = local.custom_domain
  simple_sns_additional_custom_domain       = local.additional_custom_domain
  simple_sns_existing_function_app_name     = local.existing_function_app_name
  simple_sns_enable_function_app_management = local.enable_function_app_management
  simple_sns_static_web_origin              = local.static_web_origin
  simple_sns_azure_ad_tenant_id             = local.azure_ad_tenant_id
  simple_sns_azure_ad_client_id             = local.azure_ad_client_id
  simple_sns_tags                           = local.tags

  static_site_project_name  = local.static_site_project_name
  static_site_environment   = local.static_site_environment
  static_site_enable_cdn    = local.static_site_enable_cdn
  static_site_enable_https  = local.static_site_enable_https
  static_site_custom_domain = local.static_site_custom_domain
  static_site_tags          = local.static_site_tags
}
