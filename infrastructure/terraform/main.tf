# Main Terraform configuration
# This file can contain data sources, locals, and other shared resources

# Local values for common configurations
# Note: Currently using var.tags directly in resources.
# If you want to add additional tags (like ManagedBy), use locals.common_tags instead.
locals {
  common_tags = merge(
    var.tags,
    {
      ManagedBy = "Terraform"
    }
  )
}

