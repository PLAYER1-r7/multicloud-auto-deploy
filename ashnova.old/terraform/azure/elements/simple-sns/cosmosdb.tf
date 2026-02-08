# Cosmos DB Account (NoSQL API)
resource "azurerm_cosmosdb_account" "simple_sns" {
  name                = "cosmos-${var.project_name}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.simple_sns.name
  location            = azurerm_resource_group.simple_sns.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.simple_sns.location
    failover_priority = 0
  }

  capabilities {
    name = "EnableServerless"
  }

  tags = var.tags
}

# Cosmos DB Database
resource "azurerm_cosmosdb_sql_database" "simple_sns" {
  name                = "simple-sns-db"
  resource_group_name = azurerm_cosmosdb_account.simple_sns.resource_group_name
  account_name        = azurerm_cosmosdb_account.simple_sns.name
}

# Cosmos DB Container (Posts)
resource "azurerm_cosmosdb_sql_container" "posts" {
  name                = "posts"
  resource_group_name = azurerm_cosmosdb_account.simple_sns.resource_group_name
  account_name        = azurerm_cosmosdb_account.simple_sns.name
  database_name       = azurerm_cosmosdb_sql_database.simple_sns.name
  partition_key_paths = ["/postId"]

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}
