# Production Environment Configuration
environment = "prod"

# Production-specific settings
lambda_timeout     = 300
lambda_memory      = 512
log_retention_days = 30 # Longer retention for prod

# Production should not be public
enable_public_s3_access = false

# Tags
tags = {
  Project = "RearcDataQuest"
}
