# Storage Account (frontend + images)
resource "azurerm_storage_account" "simple_sns" {
  name                     = "simplesns${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.simple_sns.name
  location                 = azurerm_resource_group.simple_sns.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = true

  blob_properties {
    versioning_enabled = true

    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["GET", "HEAD", "OPTIONS"]
      allowed_origins    = ["*"]
      exposed_headers    = ["*"]
      max_age_in_seconds = 3600
    }

    cors_rule {
      allowed_headers    = ["*"]
      allowed_methods    = ["PUT", "POST", "OPTIONS"]
      allowed_origins    = local.frontend_origins
      exposed_headers    = ["ETag", "x-ms-request-id", "x-ms-version"]
      max_age_in_seconds = 3600
    }
  }

  tags = var.tags
}

# Static Website configuration
resource "azurerm_storage_account_static_website" "simple_sns" {
  storage_account_id = azurerm_storage_account.simple_sns.id
  index_document     = "index.html"
  error_404_document = "index.html"
}

# Storage Container for images (public read)
resource "azurerm_storage_container" "images" {
  name                  = "post-images"
  storage_account_id    = azurerm_storage_account.simple_sns.id
  container_access_type = "blob"
}
