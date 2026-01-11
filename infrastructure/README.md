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
   ```bash
   cd lambda/data_sync
   pip install -r requirements.txt -t .
   
   cd ../analytics
   pip install -r requirements.txt -t .
   ```

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

## Notes

- Lambda functions need to be packaged with dependencies
- S3 event notifications require proper IAM permissions
- SQS visibility timeout should be >= Lambda timeout
- Lambda functions import from the `rearc` package, so you'll need to bundle the `src/rearc` directory in the Lambda deployment package

