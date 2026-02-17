# Existing Function App (data source)
data "azurerm_linux_function_app" "existing" {
  count               = var.enable_function_app_management ? 1 : 0
  name                = var.existing_function_app_name
  resource_group_name = azurerm_resource_group.simple_sns.name
}
