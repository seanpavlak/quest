# Terraform Backend Configuration (recreated after full reset)
terraform {
  backend "s3" {
    bucket         = "rearc-data-pipeline-terraform-state-788c706e"
    key            = "rearc-data-pipeline/dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "rearc-data-pipeline-terraform-state-lock"
  }
}
