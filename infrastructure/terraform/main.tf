# Main Terraform configuration
# This file can contain data sources, locals, and other shared resources

# Local values for common configurations
locals {
  common_tags = merge(
    var.tags,
    {
      ManagedBy = "Terraform"
    }
  )
}

