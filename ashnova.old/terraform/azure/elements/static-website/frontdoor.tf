# Azure Front Door Profile
resource "azurerm_cdn_frontdoor_profile" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name                = "afd-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.static_site.name
  sku_name            = "Standard_AzureFrontDoor"

  tags = var.tags
}

# Front Door Endpoint
resource "azurerm_cdn_frontdoor_endpoint" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name                     = "fde-${var.project_name}-${random_string.suffix.result}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.static_site[0].id

  tags = var.tags
}

# Front Door Origin Group
resource "azurerm_cdn_frontdoor_origin_group" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name                     = "fdorg-${var.project_name}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.static_site[0].id

  load_balancing {
    sample_size                 = 4
    successful_samples_required = 3
  }

  health_probe {
    protocol            = "Https"
    interval_in_seconds = 100
    path                = "/"
    request_type        = "HEAD"
  }
}

# Front Door Origin
resource "azurerm_cdn_frontdoor_origin" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name                          = "fdo-${var.project_name}"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.static_site[0].id

  enabled                        = true
  host_name                      = azurerm_storage_account.static_site.primary_web_host
  http_port                      = 80
  https_port                     = 443
  origin_host_header             = azurerm_storage_account.static_site.primary_web_host
  priority                       = 1
  weight                         = 1000
  certificate_name_check_enabled = true
}

# Front Door Route
resource "azurerm_cdn_frontdoor_route" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name                          = "fdr-${var.project_name}"
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.static_site[0].id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.static_site[0].id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.static_site[0].id]

  # カスタムドメインが設定されている場合、それも含める
  cdn_frontdoor_custom_domain_ids = var.custom_domain != "" ? [azurerm_cdn_frontdoor_custom_domain.static_site[0].id] : []

  supported_protocols    = ["Http", "Https"]
  patterns_to_match      = ["/*"]
  forwarding_protocol    = "HttpsOnly"
  link_to_default_domain = true
  https_redirect_enabled = true

  depends_on = [azurerm_cdn_frontdoor_custom_domain.static_site]
}

# Front Door Security Policy (WAF)
resource "azurerm_cdn_frontdoor_security_policy" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name                     = "fdsp-${var.project_name}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.static_site[0].id

  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.static_site[0].id

      association {
        # デフォルトエンドポイントとカスタムドメイン両方に適用
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.static_site[0].id
        }

        # カスタムドメインが設定されている場合、それも含める
        dynamic "domain" {
          for_each = var.custom_domain != "" ? [1] : []
          content {
            cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_custom_domain.static_site[0].id
          }
        }

        patterns_to_match = ["/*"]
      }
    }
  }

  depends_on = [azurerm_cdn_frontdoor_custom_domain.static_site]
}

# Custom Domain (オプション)
resource "azurerm_cdn_frontdoor_custom_domain" "static_site" {
  count = var.enable_cdn && var.custom_domain != "" ? 1 : 0

  name                     = replace(var.custom_domain, ".", "-")
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.static_site[0].id
  host_name                = var.custom_domain

  tls {
    certificate_type = "ManagedCertificate"
  }
}
