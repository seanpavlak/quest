variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "rearc-data-pipeline"
}

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "bls_source_url" {
  description = "BLS data source URL"
  type        = string
  default     = "https://download.bls.gov/pub/time.series/pr/"
}

variable "datausa_api_url" {
  description = "DataUSA API URL"
  type        = string
  default     = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"
}

variable "lambda_timeout" {
  description = "Lambda function timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory" {
  description = "Lambda function memory in MB"
  type        = number
  default     = 512
}

variable "schedule_expression" {
  description = "EventBridge schedule expression for data sync Lambda"
  type        = string
  default     = "cron(0 2 * * ? *)" # Daily at 2 AM UTC
}

variable "tags" {
  description = "Tags to apply to all resources (Environment will be set automatically from environment variable)"
  type        = map(string)
  default = {
    Project = "RearcDataQuest"
  }
}


variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
  validation {
    condition     = var.log_retention_days >= 1 && var.log_retention_days <= 3653
    error_message = "Log retention must be between 1 and 3653 days."
  }
}

variable "enable_public_s3_access" {
  description = "Enable public read access to S3 data bucket"
  type        = bool
  default     = false
}

variable "sqs_message_retention_seconds" {
  description = "SQS message retention period in seconds"
  type        = number
  default     = 345600
  validation {
    condition     = var.sqs_message_retention_seconds >= 60 && var.sqs_message_retention_seconds <= 1209600
    error_message = "SQS message retention must be between 60 and 1209600 seconds (14 days)."
  }
}

variable "enable_dlq" {
  description = "Enable Dead Letter Queues for Lambda functions"
  type        = bool
  default     = true
}

variable "s3_lifecycle_enabled" {
  description = "Enable S3 lifecycle policies for cost optimization"
  type        = bool
  default     = true
}

variable "github_repository" {
  description = "GitHub repository in format owner/repo (e.g., seanpavlak/quest)"
  type        = string
  default     = "seanpavlak/quest"
}

variable "enable_github_oidc" {
  description = "Enable GitHub OIDC provider and IAM role for CI/CD"
  type        = bool
  default     = true
}

variable "environment" {
  description = "Environment name (dev, prod, staging, etc.)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "prod", "staging"], var.environment)
    error_message = "Environment must be one of: dev, prod, staging"
  }
}
