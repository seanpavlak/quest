# Deployment Guide - Step by Step

## Overview

This guide walks you through deploying the complete data pipeline to AWS. There are 3 main issues to fix before deployment:

1. **SQS Policy** - Needs to allow S3 service principal (not IAM role)
2. **Lambda Package Size** - Analytics Lambda exceeds 70MB, needs S3 upload
3. **Initial Deployment** - First-time setup

---

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** installed and configured
3. **Terraform** installed (v1.0+)
4. **Python 3.11+** for building Lambda packages

---

## Step 1: Fix SQS Policy (S3 Service Principal)

The current SQS policy uses an IAM role, but S3 needs to send messages directly.

### File: `infrastructure/terraform/sqs.tf`

**Current (WRONG):**
```hcl
resource "aws_sqs_queue_policy" "s3_notifications" {
  queue_url = aws_sqs_queue.s3_notifications.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.s3_notifications.arn  # ❌ Wrong - IAM role doesn't exist
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.s3_notifications.arn
      }
    ]
  })
}
```

**Fix:**
```hcl
resource "aws_sqs_queue_policy" "s3_notifications" {
  queue_url = aws_sqs_queue.s3_notifications.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"  # ✅ Correct - S3 service principal
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.s3_notifications.arn
        Condition = {
          ArnLike = {
            "aws:SourceArn" = "${aws_s3_bucket.data_bucket.arn}"
          }
        }
      }
    ]
  })
}
```

**Action:** Update `infrastructure/terraform/sqs.tf` with the fix above.

---

## Step 2: Fix Lambda Package Size Issue

The Analytics Lambda includes pandas/numpy and exceeds AWS's 70MB direct upload limit. We need to upload large packages to S3 first.

### Option A: Upload Large Packages to S3 (Recommended)

This approach uploads the Lambda package to S3, then references it in Terraform.

#### Step 2.1: Create S3 Bucket for Lambda Packages

Add to `infrastructure/terraform/s3.tf`:

```hcl
# S3 Bucket for Lambda deployment packages
resource "aws_s3_bucket" "lambda_packages" {
  bucket = "${var.project_name}-lambda-packages-${random_id.bucket_suffix.hex}"

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "lambda_packages" {
  bucket = aws_s3_bucket.lambda_packages.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_packages" {
  bucket = aws_s3_bucket.lambda_packages.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
```

#### Step 2.2: Update Lambda.tf to Use S3 for Analytics Lambda

**File: `infrastructure/terraform/lambda.tf`**

Replace the Analytics Lambda section:

```hcl
# Upload Analytics Lambda package to S3
resource "aws_s3_object" "analytics_lambda_package" {
  bucket = aws_s3_bucket.lambda_packages.id
  key    = "analytics-${data.archive_file.analytics_zip.output_base64sha256}.zip"
  source = data.archive_file.analytics_zip.output_path
  etag   = data.archive_file.analytics_zip.output_base64sha256
}

# Analytics Lambda Function (using S3)
resource "aws_lambda_function" "analytics" {
  s3_bucket     = aws_s3_bucket.lambda_packages.id
  s3_key        = aws_s3_object.analytics_lambda_package.key
  function_name = "${var.project_name}-analytics"
  role          = aws_iam_role.analytics_lambda.arn
  handler       = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.analytics_zip.output_base64sha256
  runtime       = "python3.11"
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.data_bucket.id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.analytics,
    aws_iam_role_policy.analytics_lambda,
    aws_s3_object.analytics_lambda_package
  ]

  tags = var.tags
}
```

**Action:** Update `infrastructure/terraform/lambda.tf` with the S3 upload approach.

---

## Step 3: Prepare Lambda Dependencies

Before deploying, you need to install dependencies in the Lambda directories.

### Step 3.1: Install Data Sync Lambda Dependencies

```bash
cd infrastructure/lambda/data_sync
pip install -r requirements.txt -t .
cd ../../..
```

### Step 3.2: Install Analytics Lambda Dependencies

```bash
cd infrastructure/lambda/analytics
pip install -r requirements.txt -t .
cd ../../..
```

**Note:** The `.gitignore` is configured to ignore these installed packages, so they won't be committed to git.

---

## Step 4: Configure Terraform Variables

### Step 4.1: Copy Example Variables File

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

### Step 4.2: Edit terraform.tfvars

Update with your values:

```hcl
project_name = "rearc-data-pipeline"
aws_region   = "us-east-1"

# Optional: Customize schedule (default: daily at 2 AM UTC)
schedule_expression = "cron(0 2 * * ? *)"

# Optional: Customize tags
tags = {
  Project     = "RearcDataQuest"
  Environment = "dev"
  Owner       = "your-name"
}
```

---

## Step 5: Initialize and Deploy Terraform

### Step 5.1: Initialize Terraform

```bash
cd infrastructure/terraform
terraform init
```

This downloads the required providers (AWS, Archive, Random).

### Step 5.2: Review Terraform Plan

```bash
terraform plan
```

Review the plan to see what will be created:
- S3 buckets (data + lambda packages)
- IAM roles and policies
- Lambda functions
- SQS queue
- EventBridge schedule
- S3 notifications

### Step 5.3: Apply Terraform

```bash
terraform apply
```

Type `yes` when prompted. This will:
1. Create all AWS resources
2. Build Lambda packages
3. Upload Lambda functions
4. Configure all integrations

**Expected time:** 5-10 minutes

---

## Step 6: Verify Deployment

### Step 6.1: Check S3 Bucket

```bash
aws s3 ls s3://$(terraform output -raw data_bucket_name)/
```

Should be empty initially (will populate after first Lambda run).

### Step 6.2: Test Data Sync Lambda Manually

```bash
# Get Lambda function name
LAMBDA_NAME=$(terraform output -raw data_sync_lambda_name)

# Invoke manually
aws lambda invoke \
  --function-name $LAMBDA_NAME \
  --payload '{}' \
  response.json

# Check response
cat response.json
```

### Step 6.3: Check CloudWatch Logs

```bash
# Data Sync Lambda logs
aws logs tail /aws/lambda/$(terraform output -raw data_sync_lambda_name) --follow

# Analytics Lambda logs
aws logs tail /aws/lambda/$(terraform output -raw analytics_lambda_name) --follow
```

### Step 6.4: Verify S3 Data

After Lambda runs, check S3:

```bash
aws s3 ls s3://$(terraform output -raw data_bucket_name)/
```

You should see:
- BLS data files (e.g., `pr.data.0.Current`)
- Population JSON file (e.g., `population_data_20240111.json`)

---

## Step 7: Test End-to-End Pipeline

### Step 7.1: Wait for Population File Creation

When the population JSON file is created in S3:
1. S3 sends notification to SQS
2. SQS triggers Analytics Lambda
3. Analytics Lambda processes queries and logs results

### Step 7.2: Check Analytics Results

```bash
# View Analytics Lambda logs
aws logs tail /aws/lambda/$(terraform output -raw analytics_lambda_name) --follow

# Or view in AWS Console:
# CloudWatch > Log Groups > /aws/lambda/rearc-data-pipeline-analytics
```

Look for log entries with:
- Query 1 Results: `{"mean": ..., "std_dev": ...}`
- Query 2 Results: Number of records
- Query 3 Results: Number of records

---

## Step 8: Get S3 Bucket Link (For Submission)

### Step 8.1: Get Bucket Name

```bash
terraform output data_bucket_name
```

### Step 8.2: Create Public Read Access (Optional)

If you want to share the bucket link, add bucket policy:

**File: `infrastructure/terraform/s3.tf`** (add this resource):

```hcl
resource "aws_s3_bucket_policy" "public_read" {
  bucket = aws_s3_bucket.data_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.data_bucket.arn}/*"
      }
    ]
  })
}
```

Then apply:
```bash
terraform apply
```

### Step 8.3: Get Public URL

```
https://<bucket-name>.s3.amazonaws.com/
```

Or for specific file:
```
https://<bucket-name>.s3.amazonaws.com/pr.data.0.Current
```

---

## Troubleshooting

### Issue: Lambda Package Too Large

**Error:** `RequestEntityTooLargeException: Request must be smaller than 70167211 bytes`

**Solution:** Ensure Step 2 (S3 upload for Analytics Lambda) is completed.

### Issue: S3 Notification Not Working

**Error:** `Unable to validate the following destination configurations`

**Solution:** Ensure Step 1 (SQS policy fix) is completed and `terraform apply` is run.

### Issue: Lambda Timeout

**Error:** Lambda times out during BLS sync

**Solution:** Increase timeout in `terraform.tfvars`:
```hcl
lambda_timeout = 900  # 15 minutes
```

### Issue: Permission Denied

**Error:** `AccessDenied` when Lambda tries to access S3

**Solution:** Check IAM roles have correct policies. Run `terraform apply` again.

---

## Cleanup (If Needed)

To destroy all resources:

```bash
cd infrastructure/terraform
terraform destroy
```

**Warning:** This will delete all data in S3 buckets!

---

## Next Steps After Deployment

1. ✅ Monitor CloudWatch logs for errors
2. ✅ Verify daily schedule is working
3. ✅ Check S3 bucket for data files
4. ✅ Review analytics query results in logs
5. ✅ Share S3 bucket link for submission

---

## Summary Checklist

- [ ] Fix SQS policy (Step 1)
- [ ] Fix Lambda package size (Step 2)
- [ ] Install Lambda dependencies (Step 3)
- [ ] Configure Terraform variables (Step 4)
- [ ] Initialize Terraform (Step 5.1)
- [ ] Review plan (Step 5.2)
- [ ] Deploy infrastructure (Step 5.3)
- [ ] Verify deployment (Step 6)
- [ ] Test end-to-end (Step 7)
- [ ] Get S3 bucket link (Step 8)

---

## Files to Update

1. `infrastructure/terraform/sqs.tf` - Fix SQS policy
2. `infrastructure/terraform/lambda.tf` - Add S3 upload for Analytics Lambda
3. `infrastructure/terraform/s3.tf` - Add Lambda packages bucket (if using Option A)
4. `infrastructure/terraform/terraform.tfvars` - Configure your variables

---

## Estimated Time

- **Setup & Fixes:** 30 minutes
- **Terraform Deploy:** 10 minutes
- **Testing:** 15 minutes
- **Total:** ~1 hour

