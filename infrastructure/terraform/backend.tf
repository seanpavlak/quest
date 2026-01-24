# Terraform Backend Configuration
# This backend uses S3 for state storage and DynamoDB for state locking
# The state key is environment-specific to separate dev/prod states
# 
# Note: Backend configuration cannot use variables, so we use a single shared bucket
# but environment-specific state keys. The bucket and lock table are created once.
#
# State keys:
#   - dev:  rearc-data-pipeline/dev/terraform.tfstate
#   - prod: rearc-data-pipeline/prod/terraform.tfstate

terraform {
  backend "s3" {
    bucket         = "rearc-data-pipeline-terraform-state-05e6e915"
    key            = "rearc-data-pipeline/dev/terraform.tfstate" # Default to dev, override in CI/CD
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "rearc-data-pipeline-terraform-state-lock"
  }
}
