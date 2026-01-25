# Local values used across multiple files
# https://developer.hashicorp.com/terraform/language/style

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
