# Resource Group
resource "azurerm_resource_group" "simple_sns" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.azure_location
  tags     = var.tags
}

# Resource Group delete protection
resource "azurerm_management_lock" "simple_sns_rg_delete" {
  name       = "rg-${var.project_name}-${var.environment}-delete-lock"
  scope      = azurerm_resource_group.simple_sns.id
  lock_level = "CanNotDelete"
  notes      = "Protect resource group from accidental deletion"
}
