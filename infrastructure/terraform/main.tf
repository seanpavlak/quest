# Main Terraform configuration
# This file contains data sources, locals, and other shared resources

# Local values for resource naming
locals {
  # Standardized resource name prefix including environment
  resource_prefix = "${var.project_name}-${var.environment}"

  # Update tags to include environment from variable
  common_tags = merge(
    var.tags,
    {
      Environment = var.environment
    }
  )
}