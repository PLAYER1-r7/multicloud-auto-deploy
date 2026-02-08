# Front Door WAF Policy (Standard SKUはカスタムルールのみ)
resource "azurerm_cdn_frontdoor_firewall_policy" "static_site" {
  count = var.enable_cdn ? 1 : 0

  name                = replace("fdwaf${var.project_name}${var.environment}", "-", "")
  resource_group_name = azurerm_resource_group.static_site.name
  sku_name            = "Standard_AzureFrontDoor"
  mode                = "Prevention"

  # レート制限ルール
  custom_rule {
    name     = "RateLimiting"
    enabled  = true
    priority = 100
    type     = "RateLimitRule"
    action   = "Block"

    match_condition {
      match_variable     = "RemoteAddr"
      operator           = "IPMatch"
      negation_condition = false
      match_values       = ["0.0.0.0/0"]
    }

    rate_limit_duration_in_minutes = 1
    rate_limit_threshold           = 100
  }

  # 一般的な攻撃パターンのブロック（User-Agent）
  custom_rule {
    name     = "BlockMaliciousUserAgents"
    enabled  = true
    priority = 200
    type     = "MatchRule"
    action   = "Block"

    match_condition {
      match_variable     = "RequestHeader"
      selector           = "User-Agent"
      operator           = "Contains"
      negation_condition = false
      match_values = [
        "sqlmap",
        "nikto",
        "nmap",
        "masscan",
        "python-requests"
      ]
      transforms = ["Lowercase"]
    }
  }

  # 地理的制限（必要に応じて調整）
  # 注意: デフォルトで無効。有効化する場合はISO 3166-1 alpha-2国コードを使用
  custom_rule {
    name     = "GeoFiltering"
    enabled  = false # デフォルトは無効
    priority = 300
    type     = "MatchRule"
    action   = "Block"

    match_condition {
      match_variable     = "RemoteAddr"
      operator           = "GeoMatch"
      negation_condition = true
      # ISO 3166-1 alpha-2国コードを使用（例: JP, US, GB, DE, FR等）
      # match_values       = ["JP", "US"]  # 日本と米国のみ許可する場合
      match_values = ["JP"] # デフォルトは日本のみ
    }
  }
}
