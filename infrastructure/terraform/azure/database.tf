# Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  name                = "${local.resource_prefix}-cosmos"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  capabilities {
    name = "EnableServerless"
  }

  tags = local.common_tags
}

# Cosmos DB SQL Database
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "${var.project_name}-db"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

# Cosmos DB SQL Container
resource "azurerm_cosmosdb_sql_container" "messages" {
  name                = "messages"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths = ["/id"]
}
