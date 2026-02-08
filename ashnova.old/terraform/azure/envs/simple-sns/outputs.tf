output "resource_group_name" {
  value = module.simple_sns.simple_sns_resource_group_name
}

output "storage_account_name" {
  value = module.simple_sns.simple_sns_storage_account_name
}

output "static_website_url" {
  value = module.simple_sns.simple_sns_static_website_url
}

output "frontdoor_endpoint_host" {
  value = module.simple_sns.simple_sns_frontdoor_endpoint_host
}

output "frontdoor_custom_domain_validation_token" {
  value = module.simple_sns.simple_sns_frontdoor_custom_domain_validation_token
}

output "frontdoor_additional_custom_domain_validation_record" {
  value = module.simple_sns.simple_sns_frontdoor_additional_custom_domain_validation_record
}

output "function_app_name" {
  value = module.simple_sns.simple_sns_function_app_name
}

output "api_base_url" {
  value = module.simple_sns.simple_sns_api_base_url
}

output "cosmos_account_name" {
  value = module.simple_sns.simple_sns_cosmos_account_name
}

output "static_site_resource_group_name" {
  value = module.simple_sns.static_site_resource_group_name
}

output "static_site_storage_account_name" {
  value = module.simple_sns.static_site_storage_account_name
}

output "static_site_frontdoor_endpoint_host" {
  value = module.simple_sns.static_site_frontdoor_endpoint_host
}

output "static_site_custom_domain_validation_record" {
  value = module.simple_sns.static_site_custom_domain_validation_record
}

output "static_site_custom_domain_cname" {
  value = module.simple_sns.static_site_custom_domain_cname
}
