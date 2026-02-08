# Azure Front Door Standard
resource "azurerm_cdn_frontdoor_profile" "simple_sns" {
  name                = local.frontdoor_name
  resource_group_name = azurerm_resource_group.simple_sns.name
  sku_name            = "Standard_AzureFrontDoor"

  tags = var.tags
}

resource "azurerm_cdn_frontdoor_endpoint" "simple_sns" {
  name                     = "${local.frontdoor_name}-endpoint"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.simple_sns.id

  tags = var.tags
}

resource "azurerm_cdn_frontdoor_origin_group" "static" {
  name                     = "static-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.simple_sns.id

  health_probe {
    interval_in_seconds = 120
    path                = "/"
    protocol            = "Https"
    request_type        = "GET"
  }

  load_balancing {
    additional_latency_in_milliseconds = 50
    sample_size                        = 4
    successful_samples_required        = 3
  }
}

resource "azurerm_cdn_frontdoor_origin" "static" {
  name                           = "static-origin"
  cdn_frontdoor_origin_group_id  = azurerm_cdn_frontdoor_origin_group.static.id
  enabled                        = true
  host_name                      = azurerm_storage_account.simple_sns.primary_web_host
  origin_host_header             = azurerm_storage_account.simple_sns.primary_web_host
  certificate_name_check_enabled = true
  http_port                      = 80
  https_port                     = 443
  priority                       = 1
  weight                         = 1000
}

resource "azurerm_cdn_frontdoor_origin_group" "api" {
  name                     = "api-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.simple_sns.id

  health_probe {
    interval_in_seconds = 120
    path                = "/api/listposts"
    protocol            = "Https"
    request_type        = "GET"
  }

  load_balancing {
    additional_latency_in_milliseconds = 50
    sample_size                        = 4
    successful_samples_required        = 3
  }
}

resource "azurerm_cdn_frontdoor_origin" "api" {
  name                           = "api-origin"
  cdn_frontdoor_origin_group_id  = azurerm_cdn_frontdoor_origin_group.api.id
  enabled                        = true
  host_name                      = local.api_origin_hostname
  origin_host_header             = local.api_origin_hostname
  certificate_name_check_enabled = false
  http_port                      = 80
  https_port                     = 443
  priority                       = 1
  weight                         = 1000
}

resource "azurerm_cdn_frontdoor_custom_domain" "simple_sns" {
  name                     = "custom-${var.project_name}-${var.environment}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.simple_sns.id
  host_name                = var.custom_domain

  tls {
    certificate_type = "ManagedCertificate"
  }
}

resource "azurerm_cdn_frontdoor_custom_domain" "simple_sns_additional" {
  count                    = var.additional_custom_domain != "" ? 1 : 0
  name                     = "custom-${replace(var.additional_custom_domain, ".", "-")}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.simple_sns.id
  host_name                = var.additional_custom_domain

  tls {
    certificate_type = "ManagedCertificate"
  }
}

resource "azurerm_cdn_frontdoor_route" "api" {
  name                            = "api-route"
  cdn_frontdoor_endpoint_id       = azurerm_cdn_frontdoor_endpoint.simple_sns.id
  cdn_frontdoor_origin_group_id   = azurerm_cdn_frontdoor_origin_group.api.id
  cdn_frontdoor_origin_ids        = [azurerm_cdn_frontdoor_origin.api.id]
  cdn_frontdoor_custom_domain_ids = local.frontdoor_custom_domain_ids

  supported_protocols    = ["Https"]
  patterns_to_match      = ["/api/*"]
  forwarding_protocol    = "HttpsOnly"
  link_to_default_domain = true
  https_redirect_enabled = false

  depends_on = [
    azurerm_cdn_frontdoor_origin.api
  ]
}

resource "azurerm_cdn_frontdoor_route" "static" {
  name                            = "static-route"
  cdn_frontdoor_endpoint_id       = azurerm_cdn_frontdoor_endpoint.simple_sns.id
  cdn_frontdoor_origin_group_id   = azurerm_cdn_frontdoor_origin_group.static.id
  cdn_frontdoor_origin_ids        = [azurerm_cdn_frontdoor_origin.static.id]
  cdn_frontdoor_custom_domain_ids = local.frontdoor_custom_domain_ids

  supported_protocols    = ["Https"]
  patterns_to_match      = ["/*"]
  forwarding_protocol    = "HttpsOnly"
  link_to_default_domain = true
  https_redirect_enabled = false

  cache {
    compression_enabled           = true
    content_types_to_compress     = ["text/html", "text/css", "application/javascript", "application/json", "image/svg+xml"]
    query_string_caching_behavior = "IgnoreQueryString"
  }

  depends_on = [
    azurerm_cdn_frontdoor_origin.static,
    azurerm_cdn_frontdoor_route.api
  ]
}

resource "azurerm_cdn_frontdoor_firewall_policy" "simple_sns" {
  name                = "waf${replace(var.project_name, "-", "")}${replace(var.environment, "-", "")}"
  resource_group_name = azurerm_resource_group.simple_sns.name
  sku_name            = "Standard_AzureFrontDoor"
  enabled             = true
  mode                = "Prevention"

  tags = var.tags
}

resource "azurerm_cdn_frontdoor_security_policy" "simple_sns" {
  name                     = "security-${var.project_name}-${var.environment}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.simple_sns.id

  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.simple_sns.id

      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.simple_sns.id
        }

        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_custom_domain.simple_sns.id
        }

        dynamic "domain" {
          for_each = var.additional_custom_domain != "" ? [1] : []
          content {
            cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_custom_domain.simple_sns_additional[0].id
          }
        }

        patterns_to_match = ["/*"]
      }
    }
  }
}
