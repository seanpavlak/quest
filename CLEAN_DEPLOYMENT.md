# Clean Deployment Guide

## Overview

This guide walks through completely destroying all AWS resources and redeploying from scratch to ensure everything works correctly.

## Step 1: Update Configuration

### Update terraform.tfvars

```bash
cd infrastructure/terraform
```

Edit `terraform.tfvars` and ensure:
```hcl
budget_alert_email = "seanpavlak+rearc@gmail.com"
```

## Step 2: Destroy All Resources

```bash
cd infrastructure/terraform
terraform destroy
```

Type `yes` when prompted. This will delete:
- All S3 buckets (including data!)
- All Lambda functions
- All IAM roles and policies
- SQS queue
- EventBridge schedule
- CloudWatch log groups
- Budget (if created)

**Warning:** This deletes ALL data in S3 buckets!

## Step 3: Clean Local Lambda Dependencies

```bash
# Clean Analytics Lambda
cd infrastructure/lambda/analytics
rm -rf boto3 botocore requests pandas numpy pytz tzdata certifi charset_normalizer dateutil idna jmespath s3transfer urllib3 rearc *.dist-info __pycache__ bin

# Clean Data Sync Lambda (if needed)
cd ../data_sync
rm -rf boto3 botocore requests *.dist-info __pycache__ bin
```

## Step 4: Reinstall Lambda Dependencies

### Analytics Lambda (Linux-compatible)

```bash
cd infrastructure/lambda/analytics

# Install Linux-compatible packages
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir boto3
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir "numpy<2.0"
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir pandas

# Copy rearc package
mkdir -p rearc
cp -r ../../../../src/rearc/* rearc/
```

### Data Sync Lambda

```bash
cd infrastructure/lambda/data_sync
pip install -r requirements.txt -t .
```

## Step 5: Fresh Terraform Deployment

```bash
cd infrastructure/terraform

# Initialize (if needed)
terraform init

# Review plan
terraform plan

# Deploy
terraform apply
```

Type `yes` when prompted.

## Step 6: Verify Deployment

```bash
# Check all resources
terraform output

# Test Data Sync Lambda
LAMBDA=$(terraform output -raw data_sync_lambda_function_name)
aws lambda invoke --function-name $LAMBDA --payload '{}' /tmp/test.json
cat /tmp/test.json

# Check S3 bucket
BUCKET=$(terraform output -raw s3_bucket_name)
aws s3 ls s3://$BUCKET/
```

## Step 7: Test End-to-End

Run the end-to-end test script:

```bash
cd ../..
./test_e2e.sh
```

## Expected Results

✅ All resources created successfully
✅ Data Sync Lambda executes and populates S3
✅ Analytics Lambda triggers and logs query results
✅ Budget alerts configured with your email
✅ S3 bucket is publicly accessible

