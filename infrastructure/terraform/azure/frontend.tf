# Storage Account for Frontend Static Website
resource "azurerm_storage_account" "frontend" {
  name                     = "mcadfe${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  static_website {
    index_document     = "index.html"
    error_404_document = "index.html"
  }

  tags = local.common_tags
}

# Azure Front Door (CDN Profile)
resource "azurerm_cdn_frontdoor_profile" "frontend" {
  name                = "${local.resource_prefix}-afd"
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "Standard_AzureFrontDoor"
  tags                = local.common_tags
}

# Front Door Endpoint
resource "azurerm_cdn_frontdoor_endpoint" "frontend" {
  name                     = "${local.resource_prefix}-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.frontend.id
  tags                     = local.common_tags
}

# Front Door Origin Group
resource "azurerm_cdn_frontdoor_origin_group" "frontend" {
  name                     = "storage-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.frontend.id

  load_balancing {
    additional_latency_in_milliseconds = 50
    sample_size                        = 4
    successful_samples_required        = 3
  }
}

# Front Door Origin
resource "azurerm_cdn_frontdoor_origin" "frontend" {
  name                          = "storage-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.frontend.id
  enabled                       = true
  host_name                     = azurerm_storage_account.frontend.primary_web_host
  origin_host_header            = azurerm_storage_account.frontend.primary_web_host
  priority                      = 1
  weight                        = 1000
  certificate_name_check_enabled = true
}

# Front Door Route
resource "azurerm_cdn_frontdoor_route" "frontend" {
  name                          = "default-route"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.frontend.id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.frontend.id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.frontend.id]
  supported_protocols           = ["Http", "Https"]
  patterns_to_match             = ["/*"]
  link_to_default_domain        = true
  https_redirect_enabled        = true
}
