output "resource_group_name" {
  value = azurerm_resource_group.simple_sns.name
}

output "storage_account_name" {
  value = azurerm_storage_account.simple_sns.name
}

output "static_website_url" {
  value = azurerm_storage_account.simple_sns.primary_web_endpoint
}

output "frontdoor_endpoint_host" {
  value = azurerm_cdn_frontdoor_endpoint.simple_sns.host_name
}

output "frontdoor_custom_domain_validation_token" {
  value = azurerm_cdn_frontdoor_custom_domain.simple_sns.validation_token
}

output "frontdoor_additional_custom_domain_validation_record" {
  value = var.additional_custom_domain != "" ? {
    name  = "_dnsauth.${var.additional_custom_domain}"
    value = azurerm_cdn_frontdoor_custom_domain.simple_sns_additional[0].validation_token
  } : null
}

output "function_app_name" {
  value = var.enable_function_app_management ? azurerm_linux_function_app.simple_sns[0].name : null
}

output "api_base_url" {
  value = var.enable_function_app_management ? "https://${azurerm_linux_function_app.simple_sns[0].default_hostname}/api" : null
}

output "cosmos_account_name" {
  value = azurerm_cosmosdb_account.simple_sns.name
}

output "application_insights_name" {
  value = var.enable_application_insights ? azurerm_application_insights.simple_sns[0].name : null
}

output "application_insights_id" {
  value = var.enable_application_insights ? azurerm_application_insights.simple_sns[0].id : null
}
