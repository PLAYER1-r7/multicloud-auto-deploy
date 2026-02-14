# Outputs
output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.main.name
}

output "frontend_url" {
  description = "Frontend Azure Front Door URL"
  value       = "https://${azurerm_cdn_frontdoor_endpoint.frontend.host_name}"
}

output "frontend_storage_url" {
  description = "Frontend Storage Static Website URL"
  value       = azurerm_storage_account.frontend.primary_web_endpoint
}

output "api_url" {
  description = "Container App API URL"
  value       = "https://${azurerm_container_app.api.latest_revision_fqdn}"
}

output "container_app_name" {
  description = "Container App name"
  value       = azurerm_container_app.api.name
}

output "container_registry_url" {
  description = "Container Registry URL"
  value       = azurerm_container_registry.main.login_server
}

output "cosmos_endpoint" {
  description = "Cosmos DB endpoint"
  value       = azurerm_cosmosdb_account.main.endpoint
  sensitive   = true
}

output "cosmos_database_name" {
  description = "Cosmos DB database name"
  value       = azurerm_cosmosdb_sql_database.main.name
}

output "cosmos_container_name" {
  description = "Cosmos DB container name"
  value       = azurerm_cosmosdb_sql_container.messages.name
}
