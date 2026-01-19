# Terraform Backend Configuration
# This backend uses S3 for state storage and DynamoDB for state locking
terraform {
  backend "s3" {
    bucket         = "rearc-data-pipeline-terraform-state-05e6e915"
    key            = "rearc-data-pipeline/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "rearc-data-pipeline-terraform-state-lock"
  }
}
