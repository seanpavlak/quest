# Quick Start - Deployment Checklist

## ✅ Files Already Fixed

I've already fixed the critical issues in the Terraform files:

1. ✅ **SQS Policy** - Fixed in `infrastructure/terraform/sqs.tf`
   - Changed from IAM role to S3 service principal
   - Added source ARN condition

2. ✅ **Lambda Package Size** - Fixed in `infrastructure/terraform/lambda.tf`
   - Analytics Lambda now uploads to S3 first
   - Added Lambda packages bucket in `infrastructure/terraform/s3.tf`

## 🚀 Deployment Steps

### 1. Install Lambda Dependencies

```bash
# Data Sync Lambda
cd infrastructure/lambda/data_sync
pip install -r requirements.txt -t .
cd ../../..

# Analytics Lambda  
cd infrastructure/lambda/analytics
pip install -r requirements.txt -t .
cd ../../..
```

### 2. Configure Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values (optional)
```

### 3. Deploy

```bash
terraform init
terraform plan    # Review what will be created
terraform apply   # Type 'yes' to deploy
```

### 4. Test

```bash
# Get bucket name
terraform output data_bucket_name

# Manually trigger data sync Lambda
LAMBDA_NAME=$(terraform output -raw data_sync_lambda_name)
aws lambda invoke --function-name $LAMBDA_NAME --payload '{}' response.json

# Check logs
aws logs tail /aws/lambda/$LAMBDA_NAME --follow
```

### 5. Get S3 Link

```bash
BUCKET=$(terraform output -raw data_bucket_name)
echo "https://$BUCKET.s3.amazonaws.com/"
```

## ⚠️ Important Notes

- **Lambda dependencies** must be installed before `terraform apply`
- **First deployment** takes ~10 minutes
- **Daily schedule** runs at 2 AM UTC (configurable in `terraform.tfvars`)
- **S3 bucket** will be empty until first Lambda execution

## 📋 What Gets Created

- 2 S3 buckets (data + lambda packages)
- 2 Lambda functions (data sync + analytics)
- 1 SQS queue
- 1 EventBridge schedule (daily)
- IAM roles and policies
- CloudWatch log groups

## 🔍 Verify Everything Works

1. Check S3 bucket has data files after Lambda runs
2. Check CloudWatch logs for Analytics Lambda (should trigger when JSON file created)
3. Verify EventBridge schedule is enabled

## 📚 Full Details

See `DEPLOYMENT_GUIDE.md` for complete step-by-step instructions and troubleshooting.

