output "simple_sns_resource_group_name" {
  value = var.enable_simple_sns ? module.simple_sns[0].resource_group_name : null
}

output "simple_sns_storage_account_name" {
  value = var.enable_simple_sns ? module.simple_sns[0].storage_account_name : null
}

output "simple_sns_static_website_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].static_website_url : null
}

output "simple_sns_frontdoor_endpoint_host" {
  value = var.enable_simple_sns ? module.simple_sns[0].frontdoor_endpoint_host : null
}

output "simple_sns_frontdoor_custom_domain_validation_token" {
  value = var.enable_simple_sns ? module.simple_sns[0].frontdoor_custom_domain_validation_token : null
}

output "simple_sns_frontdoor_additional_custom_domain_validation_record" {
  value = var.enable_simple_sns ? module.simple_sns[0].frontdoor_additional_custom_domain_validation_record : null
}

output "simple_sns_function_app_name" {
  value = var.enable_simple_sns ? module.simple_sns[0].function_app_name : null
}

output "simple_sns_api_base_url" {
  value = var.enable_simple_sns ? module.simple_sns[0].api_base_url : null
}

output "simple_sns_cosmos_account_name" {
  value = var.enable_simple_sns ? module.simple_sns[0].cosmos_account_name : null
}

output "simple_sns_application_insights_name" {
  value = var.enable_simple_sns ? module.simple_sns[0].application_insights_name : null
}

output "simple_sns_application_insights_id" {
  value = var.enable_simple_sns ? module.simple_sns[0].application_insights_id : null
}

output "static_site_resource_group_name" {
  value = var.enable_static_site ? module.static_website[0].resource_group_name : null
}

output "static_site_storage_account_name" {
  value = var.enable_static_site ? module.static_website[0].storage_account_name : null
}

output "static_site_storage_account_primary_web_endpoint" {
  value = var.enable_static_site ? module.static_website[0].storage_account_primary_web_endpoint : null
}

output "static_site_storage_account_primary_web_host" {
  value = var.enable_static_site ? module.static_website[0].storage_account_primary_web_host : null
}

output "static_site_frontdoor_endpoint_url" {
  value = var.enable_static_site ? module.static_website[0].frontdoor_endpoint_url : null
}

output "static_site_frontdoor_endpoint_host" {
  value = var.enable_static_site ? module.static_website[0].frontdoor_endpoint_host : null
}

output "static_site_website_url" {
  value = var.enable_static_site ? module.static_website[0].website_url : null
}

output "static_site_custom_domain" {
  value = var.enable_static_site ? module.static_website[0].custom_domain : null
}

output "static_site_custom_domain_validation_record" {
  value = var.enable_static_site ? module.static_website[0].custom_domain_validation_record : null
}

output "static_site_custom_domain_cname" {
  value = var.enable_static_site ? module.static_website[0].custom_domain_cname : null
}
