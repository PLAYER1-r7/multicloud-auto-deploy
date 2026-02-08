output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.static_site.name
}

output "storage_account_name" {
  description = "Storage account name"
  value       = azurerm_storage_account.static_site.name
}

output "storage_account_primary_web_endpoint" {
  description = "Storage account primary web endpoint"
  value       = azurerm_storage_account.static_site.primary_web_endpoint
}

output "storage_account_primary_web_host" {
  description = "Storage account primary web host"
  value       = azurerm_storage_account.static_site.primary_web_host
}

output "frontdoor_endpoint_url" {
  description = "Front Door endpoint URL"
  value       = var.enable_cdn ? "https://${azurerm_cdn_frontdoor_endpoint.static_site[0].host_name}" : null
}

output "frontdoor_endpoint_host" {
  description = "Front Door endpoint hostname"
  value       = var.enable_cdn ? azurerm_cdn_frontdoor_endpoint.static_site[0].host_name : null
}

output "website_url" {
  description = "Website URL"
  value       = var.enable_cdn ? (var.custom_domain != "" ? "https://${var.custom_domain}" : "https://${azurerm_cdn_frontdoor_endpoint.static_site[0].host_name}") : azurerm_storage_account.static_site.primary_web_endpoint
}

output "custom_domain" {
  description = "Custom domain name"
  value       = var.custom_domain
}

output "custom_domain_validation_record" {
  description = "DNS validation record for custom domain"
  value = var.enable_cdn && var.custom_domain != "" ? {
    name  = "_dnsauth.${var.custom_domain}"
    type  = "TXT"
    value = azurerm_cdn_frontdoor_custom_domain.static_site[0].validation_token
  } : null
}

output "custom_domain_cname" {
  description = "CNAME record for custom domain"
  value = var.enable_cdn && var.custom_domain != "" ? {
    name  = var.custom_domain
    type  = "CNAME"
    value = azurerm_cdn_frontdoor_endpoint.static_site[0].host_name
  } : null
}
