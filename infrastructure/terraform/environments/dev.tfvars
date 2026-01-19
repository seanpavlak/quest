# Development Environment Configuration
environment = "dev"

# Development-specific settings
lambda_timeout = 300
lambda_memory  = 512
log_retention_days = 7

# Enable public access for dev (if needed for testing)
enable_public_s3_access = true

# Tags
tags = {
  Project     = "RearcDataQuest"
}
