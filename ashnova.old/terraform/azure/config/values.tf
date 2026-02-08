locals {
  azure_subscription_id = "29031d24-d41a-4f97-8362-46b40129a7e8"
  azure_location        = "japaneast"

  simple_sns_project_name                   = "simple-sns"
  simple_sns_environment                    = "prod"
  simple_sns_custom_domain                  = "sns.azure.ashnova.jp"
  simple_sns_additional_custom_domain       = ""
  simple_sns_existing_function_app_name     = "simple-sns-func-i0hj8w"
  simple_sns_enable_function_app_management = true
  simple_sns_static_web_origin              = ""
  simple_sns_azure_ad_tenant_id             = "a3182bec-d835-4ce3-af06-04579abf597e"
  simple_sns_azure_ad_client_id             = "00433640-13d1-4482-aa1b-db5f039197bf"
  simple_sns_tags = {
    Project     = "ashnova-simple-sns"
    ManagedBy   = "OpenTofu"
    Environment = "production"
    Platform    = "Azure"
  }

  static_site_project_name  = "ashnova"
  static_site_environment   = "production"
  static_site_enable_cdn    = true
  static_site_enable_https  = false
  static_site_custom_domain = "www.azure.ashnova.jp"
  static_site_tags = {
    Project     = "ashnova"
    ManagedBy   = "OpenTofu"
    Environment = "production"
  }
}

output "azure_subscription_id" {
  value = local.azure_subscription_id
}

output "azure_location" {
  value = local.azure_location
}

output "simple_sns_project_name" {
  value = local.simple_sns_project_name
}

output "simple_sns_environment" {
  value = local.simple_sns_environment
}

output "simple_sns_custom_domain" {
  value = local.simple_sns_custom_domain
}

output "simple_sns_additional_custom_domain" {
  value = local.simple_sns_additional_custom_domain
}

output "simple_sns_existing_function_app_name" {
  value = local.simple_sns_existing_function_app_name
}

output "simple_sns_enable_function_app_management" {
  value = local.simple_sns_enable_function_app_management
}

output "simple_sns_static_web_origin" {
  value = local.simple_sns_static_web_origin
}

output "simple_sns_azure_ad_tenant_id" {
  value = local.simple_sns_azure_ad_tenant_id
}

output "simple_sns_azure_ad_client_id" {
  value = local.simple_sns_azure_ad_client_id
}

output "simple_sns_tags" {
  value = local.simple_sns_tags
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

output "static_site_enable_https" {
  value = local.static_site_enable_https
}

output "static_site_custom_domain" {
  value = local.static_site_custom_domain
}

output "static_site_tags" {
  value = local.static_site_tags
}
