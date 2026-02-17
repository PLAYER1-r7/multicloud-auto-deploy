# Random suffix for globally unique names
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  resource_suffix = "${var.environment}-${random_string.suffix.result}"
  frontend_origins = compact([
    var.static_web_origin != "" ? var.static_web_origin : null,
    "https://${var.custom_domain}",
    var.additional_custom_domain != "" ? "https://${var.additional_custom_domain}" : null,
    "http://localhost:5173",
    "http://localhost:5174",
  ])
  frontdoor_name      = "afd-${var.project_name}-${random_string.suffix.result}"
  api_origin_hostname = var.existing_function_app_name != "" ? "${var.existing_function_app_name}.azurewebsites.net" : "example.invalid"
  app_insights_name   = "${var.project_name}-appinsights"
  frontdoor_custom_domain_ids = concat(
    [azurerm_cdn_frontdoor_custom_domain.simple_sns.id],
    var.additional_custom_domain != "" ? [azurerm_cdn_frontdoor_custom_domain.simple_sns_additional[0].id] : []
  )
}
