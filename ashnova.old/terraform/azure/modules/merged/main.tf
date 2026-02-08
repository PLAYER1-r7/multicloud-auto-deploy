module "simple_sns" {
  count  = var.enable_simple_sns ? 1 : 0
  source = "../../elements/simple-sns"

  azure_subscription_id          = var.azure_subscription_id
  azure_location                 = var.azure_location
  project_name                   = var.simple_sns_project_name
  environment                    = var.simple_sns_environment
  custom_domain                  = var.simple_sns_custom_domain
  additional_custom_domain       = var.simple_sns_additional_custom_domain
  existing_function_app_name     = var.simple_sns_existing_function_app_name
  enable_function_app_management = var.simple_sns_enable_function_app_management
  static_web_origin              = var.simple_sns_static_web_origin
  azure_ad_tenant_id             = var.simple_sns_azure_ad_tenant_id
  azure_ad_client_id             = var.simple_sns_azure_ad_client_id
  tags                           = var.simple_sns_tags
}

module "static_website" {
  count  = var.enable_static_site ? 1 : 0
  source = "../../elements/static-website"

  azure_location        = var.azure_location
  azure_subscription_id = var.azure_subscription_id
  project_name          = var.static_site_project_name
  environment           = var.static_site_environment
  enable_cdn            = var.static_site_enable_cdn
  enable_https          = var.static_site_enable_https
  custom_domain         = var.static_site_custom_domain
  tags                  = var.static_site_tags
}
