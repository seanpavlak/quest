# Infrastructure

This directory contains the infrastructure as code for deploying the data pipeline to AWS.

## Structure

```
infrastructure/
├── terraform/          # Terraform configuration
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── providers.tf
│   ├── s3.tf
│   ├── iam.tf
│   ├── lambda.tf
│   ├── sqs.tf
│   ├── eventbridge.tf
│   ├── s3_notifications.tf
│   └── terraform.tfvars.example
└── lambda/             # Lambda function code
    ├── data_sync/
    │   ├── lambda_function.py
    │   └── requirements.txt
    └── analytics/
        ├── lambda_function.py
        └── requirements.txt
```

## Prerequisites

1. Install Terraform (>= 1.0):
   ```bash
   brew install terraform  # macOS
   # or download from https://www.terraform.io/downloads
   ```

2. Configure AWS credentials:
   ```bash
   aws configure
   ```

3. Install Python dependencies for Lambda functions:

   **Data Sync Lambda** (standard installation):
   ```bash
   cd lambda/data_sync
   pip install -r requirements.txt -t .
   mkdir -p rearc
   cp -r ../../../../src/rearc/* rearc/
   ```

   **Analytics Lambda** (Linux-compatible installation required):
   
   The Analytics Lambda uses numpy and pandas which require Linux-compatible binaries. Use:
   
   ```bash
   cd lambda/analytics
   
   # Install Linux-compatible dependencies
   pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir boto3
   pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir "numpy<2.0"
   pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir pandas
   
   # Copy rearc package
   mkdir -p rearc
   cp -r ../../../../src/rearc/* rearc/
   ```
   
   **Note**: The Analytics Lambda package is >70MB, so Terraform uploads it to S3 first (`lambda_packages` bucket), then references it from there.

## Deployment

1. Navigate to terraform directory:
   ```bash
   cd terraform
   ```

2. Copy and configure variables:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

3. Initialize Terraform:
   ```bash
   terraform init
   ```

4. Review planned changes:
   ```bash
   terraform plan
   ```

5. Apply configuration:
   ```bash
   terraform apply
   ```

6. Note the outputs (S3 bucket name, Lambda ARNs, etc.)

## Testing

1. **Test Data Sync Lambda manually**:
   ```bash
   aws lambda invoke \
     --function-name <data-sync-function-name> \
     --payload '{}' \
     response.json
   ```

2. **Check CloudWatch Logs**:
   ```bash
   aws logs tail /aws/lambda/<function-name> --follow
   ```

3. **Verify S3 bucket contents**:
   ```bash
   aws s3 ls s3://<bucket-name>/
   ```

## Cleanup

To destroy all resources:
```bash
terraform destroy
```

## Important Notes

- **Lambda Dependencies**: 
  - Data Sync Lambda uses standard `pip install`
  - Analytics Lambda requires Linux-compatible packages (installed via `--platform manylinux2014_x86_64`)
  - Both Lambda functions need the `rearc` package copied from `src/rearc/`

- **Package Size**:
  - Analytics Lambda package is >70MB, so it's uploaded to S3 (`lambda_packages` bucket) first
  - Terraform handles this automatically via `aws_s3_object.analytics_lambda_package`

- **S3 Buckets**:
  - `data_bucket`: Publicly readable, stores BLS and population data
  - `lambda_packages`: Private bucket for storing large Lambda deployment packages

- **S3 Event Notifications**:
  - Configured to send messages to SQS when `population_data_*.json` files are created
  - Analytics Lambda is triggered via SQS event source mapping

- **IAM Permissions**:
  - Lambda roles have least-privilege access
  - SQS queue policy allows S3 service to send messages

- **Cost Management**:
  - Budget should be created manually in AWS Console (requires special IAM permissions)
  - Go to AWS Billing Console > Budgets to set up cost alerts

