# Rearc Data Quest - Complete Deployment Guide

This comprehensive guide provides detailed information about the architecture, code implementation, and step-by-step instructions for deploying and managing the data pipeline infrastructure.

---

## Table of Contents

1. [S3 Bucket Information](#s3-bucket-information)
2. [Architecture Overview](#architecture-overview)
3. [Code Implementation Details](#code-implementation-details)
4. [Infrastructure Deployment](#infrastructure-deployment)
5. [Managing Terraform State](#managing-terraform-state)
6. [Troubleshooting](#troubleshooting)

---

## S3 Bucket Information

### Current S3 Bucket

**Bucket Name:** `rearc-data-pipeline-data-08041c62`  
**Bucket URL:** https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/  
**Region:** us-east-1

**Example URLs:**
- BLS Data (root directory): https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/
- Main BLS file: https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/pr.data.0.Current
- Population data pattern: https://rearc-data-pipeline-data-08041c62.s3.us-east-1.amazonaws.com/population_data_*.json

### Infrastructure Outputs File

All infrastructure outputs are captured in `config/outputs.json` for easy access. This file contains:
- S3 bucket name, ARN, and URLs
- Lambda function names and ARNs
- SQS queue URLs and ARNs
- CloudWatch log group names
- Example URLs for accessing data

**View the outputs file:**
```bash
cat config/outputs.json
```

**Extract specific values:**
```bash
# Get bucket name
cat config/outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['s3_bucket_name'])"

# Get bucket URL
cat config/outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['s3_bucket_url'])"
```

### Getting/Refreshing the S3 Bucket Link

After deploying or updating the infrastructure, refresh the outputs file:

**Option 1: Use the refresh script (recommended)**
```bash
./scripts/refresh_outputs.sh
```

**Option 2: Manual refresh from Terraform**
```bash
cd infrastructure/terraform
terraform output -json > ../../outputs_raw.json

# Then process it (or use the script)
./scripts/refresh_outputs.sh
```

**Option 3: Get bucket name directly from Terraform**
```bash
cd infrastructure/terraform
terraform output -raw s3_bucket_name
```

**S3 Bucket URL Format:**
```
https://<bucket-name>.s3.<region>.amazonaws.com/<object-key>
```

**To list all objects in the bucket:**
```bash
# Get bucket name from config/outputs.json
BUCKET_NAME=$(cat config/outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['s3_bucket_name'])")

# List all objects
aws s3 ls s3://$BUCKET_NAME/ --recursive

# Or use the URL directly
aws s3 ls s3://rearc-data-pipeline-data-08041c62/ --recursive
```

**Note:** The bucket name includes a random suffix to ensure uniqueness. After deployment, the outputs file (`config/outputs.json`) is automatically updated with the current bucket name and all other infrastructure outputs.

---

## Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     AWS Data Pipeline                            │
└─────────────────────────────────────────────────────────────────┘

1. Scheduled Trigger (EventBridge)
   │
   │ Daily Cron: cron(0 2 * * ? *)  (2 AM UTC)
   │
   ▼
2. Data Sync Lambda Function
   │
   ├─► Part 1: BLS Data Sync
   │   │
   │   └─► Syncs all files from BLS website to S3
   │       - Dynamic file discovery (iterative directory traversal)
   │       - Change detection (MD5 comparison)
   │       - Handles additions, updates, deletions
   │
   └─► Part 2: Population API Fetch
       │
       └─► Fetches data from DataUSA API
           - Saves as JSON file with timestamp
           - Example: population_data_20241201_020000.json

3. S3 Bucket (Data Storage)
   │
   │ Contains:
   │ - BLS time-series files (pr.data.0.Current, etc.)
   │ - Population JSON files (population_data_*.json)
   │
   │ (JSON file created) ──┐
   │                       │
   ▼                       │
4. S3 Event Notification   │
   │                       │
   │ Filters:              │
   │ - Prefix: population_data_ │
   │ - Suffix: .json       │
   │                       │
   ▼                       │
5. SQS Queue               │
   │                       │
   │ Receives S3 event     │
   │ messages              │
   │                       │
   ▼                       │
6. Analytics Lambda        │
   │                       │
   │ Triggered by SQS      │
   │ messages              │
   │                       │
   ├─► Query 1: Population Statistics
   │   - Mean and std dev (2013-2018)
   │
   ├─► Query 2: Best Year per Series
   │   - For each series_id, find year with max sum of values
   │
   └─► Query 3: Combined Report
       - PRS30006032 Q01 + Population data
       - Joined by year

7. CloudWatch Logs
   │
   └─► All Lambda execution logs
       - Data sync operations
       - Analytics query results
```

### Component Details

#### 1. EventBridge (CloudWatch Events)
- **Purpose**: Schedule daily execution of data sync Lambda
- **Schedule**: Daily at 2 AM UTC (configurable via `schedule_expression` variable)
- **Configuration**: `infrastructure/terraform/eventbridge.tf`

#### 2. Data Sync Lambda Function
- **Function Name**: `{project_name}-data-sync`
- **Runtime**: Python 3.11
- **Timeout**: 300 seconds (5 minutes)
- **Memory**: 512 MB
- **Handler**: `lambda_function.lambda_handler`
- **Source**: `infrastructure/lambda/data_sync/`
- **Purpose**: Executes both Part 1 (BLS sync) and Part 2 (Population fetch)

#### 3. S3 Bucket
- **Bucket Name**: `{project_name}-data-{random_suffix}`
- **Features**:
  - Versioning enabled
  - Server-side encryption (AES256)
  - Public read access (for submission requirements)
  - Lifecycle policies (optional)
- **Configuration**: `infrastructure/terraform/s3.tf`

#### 4. S3 Event Notifications
- **Trigger**: Object creation events
- **Filter**: Prefix `population_data_`, Suffix `.json`
- **Destination**: SQS Queue
- **Configuration**: `infrastructure/terraform/s3_notifications.tf`

#### 5. SQS Queue
- **Queue Name**: `{project_name}-s3-notifications`
- **Message Retention**: 4 days (345600 seconds)
- **Visibility Timeout**: 5 minutes (300 seconds)
- **Purpose**: Buffer S3 events for Analytics Lambda
- **Configuration**: `infrastructure/terraform/sqs.tf`

#### 6. Analytics Lambda Function
- **Function Name**: `{project_name}-analytics`
- **Runtime**: Python 3.11
- **Timeout**: 300 seconds (5 minutes)
- **Memory**: 512 MB
- **Handler**: `lambda_function.lambda_handler`
- **Source**: `infrastructure/lambda/analytics/`
- **Dependencies**: pandas, numpy (requires Linux-compatible packages)
- **Package Size**: >70MB (deployed via S3)
- **Trigger**: SQS event source mapping
- **Purpose**: Executes Part 3 analytics queries

#### 7. CloudWatch Logs
- **Log Groups**:
  - `/aws/lambda/{project_name}-data-sync`
  - `/aws/lambda/{project_name}-analytics`
- **Retention**: 7 days
- **Purpose**: Store Lambda execution logs and analytics results

---

## Code Implementation Details

### Part 1: BLS Data Sync (`src/rearc/data_sync/bls.py`)

The BLS data sync module implements a robust synchronization mechanism that:

1. **Dynamic File Discovery**
   - Uses iterative directory traversal (breadth-first with a queue)
   - Parses Apache-style HTML directory listings
   - Discovers files and subdirectories recursively
   - No hardcoded file names

2. **Change Detection**
   - Compares MD5 hashes of local content vs. S3 ETags
   - Only uploads new or changed files
   - Skips files that haven't changed (efficient)

3. **File Management**
   - Handles file additions (new files in source)
   - Handles file updates (changed files)
   - Handles file deletions (removes files from S3 that no longer exist in source)
   - Preserves directory structure in S3

4. **BLS Compliance**
   - Includes User-Agent header with contact information
   - Complies with BLS data access policies
   - Prevents 403 Forbidden errors

**Key Functions:**
- `sync_bls_data()`: Main entry point
- `sync_directory_iterative()`: Iterative directory traversal
- `discover_files_and_directories()`: Parse HTML directory listing
- `sync_file()`: Sync individual file (with change detection)
- `calculate_md5()`: Calculate MD5 hash for comparison
- `get_s3_object_etag()`: Get S3 object ETag (MD5)

**Example Usage:**
```python
from rearc.data_sync import sync_bls_data

# Sync BLS data to S3
sync_bls_data('my-bucket', region='us-east-1')
```

### Part 2: Population API Fetch (`src/rearc/data_sync/population.py`)

The population data module fetches data from the DataUSA API and saves it to S3:

1. **API Fetching**
   - Fetches data from DataUSA API endpoint
   - Handles errors gracefully
   - Validates JSON response

2. **S3 Storage**
   - Saves data as JSON file
   - Uses timestamp-based naming: `population_data_YYYYMMDD_HHMMSS.json`
   - Each fetch creates a new file (preserves history)

**Key Functions:**
- `fetch_and_save_population_data()`: Main entry point
- `fetch_population_data()`: Fetch data from API
- `save_to_s3()`: Save JSON to S3

**Example Usage:**
```python
from rearc.data_sync import fetch_and_save_population_data

# Fetch and save population data
fetch_and_save_population_data('my-bucket', region='us-east-1')
```

### Part 3: Analytics Queries (`src/rearc/analytics/queries.py`)

The analytics module implements three analytical queries:

#### Query 1: Population Statistics
- **Purpose**: Calculate mean and standard deviation of US population (2013-2018)
- **Function**: `query1_population_stats()`
- **Input**: Population DataFrame
- **Output**: Dictionary with `mean` and `std_dev` keys

#### Query 2: Best Year per Series
- **Purpose**: For each series_id, find the year with maximum sum of values
- **Function**: `query2_best_year_per_series()`
- **Input**: BLS DataFrame
- **Output**: DataFrame with columns: `series_id`, `year`, `value`
- **Logic**: 
  - Groups by series_id and year
  - Sums values for all quarters in each year
  - Selects year with maximum sum for each series_id

#### Query 3: Combined Report
- **Purpose**: Combine BLS data (PRS30006032 Q01) with population data
- **Function**: `query3_combined_report()`
- **Input**: BLS DataFrame, Population DataFrame
- **Output**: DataFrame with columns: `series_id`, `year`, `period`, `value`, `Population`
- **Logic**:
  - Filters BLS data for series_id = PRS30006032 and period = Q01
  - Joins with population data on year (left join)
  - Handles missing population data gracefully

**Data Cleaning:**
- Trims whitespace from string columns
- Converts numeric columns to proper types
- Handles missing values appropriately

**Example Usage:**
```python
from rearc.analytics import (
    query1_population_stats,
    query2_best_year_per_series,
    query3_combined_report
)

# Load data (example)
import pandas as pd
bls_df = pd.read_csv('pr.data.0.Current', sep='\t')
population_df = pd.DataFrame(population_data['data'])

# Run queries
stats = query1_population_stats(population_df)
best_years = query2_best_year_per_series(bls_df)
combined = query3_combined_report(bls_df, population_df)
```

### Lambda Functions

#### Data Sync Lambda (`infrastructure/lambda/data_sync/lambda_function.py`)

**Handler Function:**
```python
def lambda_handler(event, context):
    """
    Executes both BLS sync and Population fetch operations.
    
    Environment Variables:
    - S3_BUCKET_NAME: Name of the S3 bucket
    - AWS_REGION: AWS region (default: us-east-1)
    
    Returns:
    - Status code and results dictionary
    """
```

**Execution Flow:**
1. Reads S3_BUCKET_NAME from environment variables
2. Executes `sync_bls_data()` for Part 1
3. Executes `fetch_and_save_population_data()` for Part 2
4. Returns status and results

#### Analytics Lambda (`infrastructure/lambda/analytics/lambda_function.py`)

**Handler Function:**
```python
def lambda_handler(event, context):
    """
    Processes SQS messages triggered by S3 events.
    
    Execution Flow:
    1. Parses SQS event (S3 notification)
    2. Extracts S3 object key (population_data_*.json)
    3. Loads population data from S3
    4. Loads BLS data from S3 (pr.data.0.Current)
    5. Runs all 3 analytics queries
    6. Logs results to CloudWatch
    """
```

**SQS Event Processing:**
- Handles both direct S3 format and SNS-wrapped format
- Filters for population_data_*.json files
- Loads data from S3 into pandas DataFrames
- Executes all three queries
- Logs results for visibility

---

## Infrastructure Deployment

### Prerequisites

1. **AWS Account**: Active AWS account with appropriate permissions
2. **AWS CLI**: Installed and configured
   ```bash
   aws configure
   ```
3. **Terraform**: Version >= 1.0
   ```bash
   # macOS
   brew install terraform
   
   # Linux/Windows
   # Download from https://www.terraform.io/downloads
   ```
4. **Python**: Version 3.9+ (for local development and Lambda dependencies)

### Step 1: Prepare Lambda Dependencies

Before deploying with Terraform, you need to install Python dependencies for the Lambda functions.

#### Data Sync Lambda

```bash
cd infrastructure/lambda/data_sync

# Install dependencies locally
pip install -r requirements.txt -t .

# Copy rearc package
mkdir -p rearc
cp -r ../../../src/rearc/* rearc/

# Clean up (optional)
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

#### Analytics Lambda

The Analytics Lambda requires Linux-compatible packages (pandas, numpy). Use platform-specific installation:

```bash
cd infrastructure/lambda/analytics

# Install Linux-compatible dependencies
pip install --platform manylinux2014_x86_64 --target . \
    --implementation cp --python-version 3.11 \
    --only-binary=:all: --no-cache-dir boto3

pip install --platform manylinux2014_x86_64 --target . \
    --implementation cp --python-version 3.11 \
    --only-binary=:all: --no-cache-dir "numpy<2.0"

pip install --platform manylinux2014_x86_64 --target . \
    --implementation cp --python-version 3.11 \
    --only-binary=:all: --no-cache-dir pandas

# Copy rearc package
mkdir -p rearc
cp -r ../../../src/rearc/* rearc/

# Clean up (optional)
find . -type d -name "__pycache__" -exec rm -r {} +
find . -type f -name "*.pyc" -delete
```

**Note**: The Analytics Lambda package will be >70MB, so Terraform automatically uploads it to an S3 bucket (`lambda_packages`) first, then references it from there.

### Step 2: Configure Terraform Variables

```bash
cd infrastructure/terraform

# Copy example variables file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
# You can customize:
# - project_name: Prefix for all resources
# - aws_region: AWS region (default: us-east-1)
# - schedule_expression: Cron expression for daily schedule
# - lambda_timeout: Lambda timeout in seconds
# - lambda_memory: Lambda memory in MB
# - tags: Resource tags
```

**Example `terraform.tfvars`:**
```hcl
project_name = "rearc-data-pipeline"
aws_region   = "us-east-1"

bls_source_url = "https://download.bls.gov/pub/time.series/pr/"
datausa_api_url = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"

lambda_timeout = 300
lambda_memory  = 512

schedule_expression = "cron(0 2 * * ? *)"  # Daily at 2 AM UTC

tags = {
  Project     = "RearcDataQuest"
  Environment = "dev"
}
```

### Step 3: Initialize Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform (downloads providers, sets up backend)
terraform init
```

This will:
- Download the AWS provider
- Set up the Terraform backend
- Download any required modules

### Step 4: Review Terraform Plan

Before applying changes, always review the plan:

```bash
# Generate and review the execution plan
terraform plan

# Save plan to file (optional)
terraform plan -out=tfplan
```

The plan shows:
- Resources to be created
- Resources to be modified
- Resources to be destroyed
- Attribute values

**Expected Resources:**
- S3 buckets (data + lambda_packages)
- IAM roles and policies
- Lambda functions (data_sync + analytics)
- CloudWatch Log Groups
- EventBridge rule and target
- SQS queue and policy
- S3 bucket notifications
- Lambda event source mappings

### Step 5: Apply Terraform Configuration

```bash
# Apply the configuration (creates/updates resources)
terraform apply

# Or use saved plan
terraform apply tfplan

# Auto-approve (skip confirmation prompt)
terraform apply -auto-approve
```

**During apply:**
- Terraform will create all resources
- This typically takes 2-5 minutes
- You'll see progress updates
- Review the output carefully

### Step 6: Capture Outputs

After successful deployment, capture the outputs:

**Option 1: Use the refresh script (recommended)**
```bash
# From the repo root, refresh config/outputs.json
./scripts/refresh_outputs.sh
```

This script:
- Extracts all Terraform outputs
- Creates/updates `config/outputs.json`
- Includes S3 bucket URLs and example URLs
- Makes outputs easily accessible across the repository

**Option 2: Manual capture from Terraform**
```bash
# View all outputs
terraform output

# View specific output
terraform output s3_bucket_name
terraform output s3_bucket_arn

# Save raw outputs to file
terraform output -json > outputs_raw.json

# Get raw value (for scripts)
terraform output -raw s3_bucket_name
```

**Accessing outputs from `config/outputs.json`:**
```bash
# View the outputs file
cat config/outputs.json

# Get specific values using Python/jq
cat config/outputs.json | python3 -c "import sys, json; print(json.load(sys.stdin)['s3_bucket_name'])"
cat config/outputs.json | jq -r '.s3_bucket_name'
cat config/outputs.json | jq -r '.s3_bucket_url'
```

**Important Outputs:**
- `s3_bucket_name`: Name of the data bucket (for sharing links)
- `s3_bucket_url`: Full S3 bucket URL
- `s3_bucket_arn`: ARN of the data bucket
- `data_sync_lambda_function_name`: Name of data sync Lambda
- `analytics_lambda_function_name`: Name of analytics Lambda
- `sqs_queue_url`: URL of SQS queue
- CloudWatch log group names
- `example_urls`: Example URLs for accessing data

**Note:** The `config/outputs.json` file includes all infrastructure outputs in a simplified format with additional metadata like bucket URLs.

### Step 7: Verify Deployment

#### Check S3 Bucket

```bash
# Get bucket name
BUCKET_NAME=$(terraform output -raw s3_bucket_name)

# List bucket contents
aws s3 ls s3://$BUCKET_NAME/

# Check bucket policy
aws s3api get-bucket-policy --bucket $BUCKET_NAME
```

#### Test Data Sync Lambda

```bash
# Get function name
FUNC_NAME=$(terraform output -raw data_sync_lambda_function_name)

# Invoke Lambda manually
aws lambda invoke \
    --function-name $FUNC_NAME \
    --payload '{}' \
    response.json

# Check response
cat response.json

# Check logs
aws logs tail /aws/lambda/$FUNC_NAME --follow
```

#### Check EventBridge Schedule

```bash
# List EventBridge rules
aws events list-rules --name-prefix rearc-data-pipeline

# Check rule details
aws events describe-rule --name rearc-data-pipeline-daily-schedule
```

#### Verify SQS Queue

```bash
# Get queue URL
QUEUE_URL=$(terraform output -raw sqs_queue_url)

# Get queue attributes
aws sqs get-queue-attributes \
    --queue-url $QUEUE_URL \
    --attribute-names All
```

---

## Managing Terraform State

### Refreshing Terraform State

If resources have been modified outside of Terraform (e.g., via AWS Console), refresh the state:

```bash
cd infrastructure/terraform

# Refresh state (doesn't modify resources, just updates state)
terraform refresh

# Refresh and show plan
terraform plan -refresh=true
```

### Updating Infrastructure

To update infrastructure after code changes:

#### 1. Update Lambda Code

```bash
# After modifying Lambda code, reinstall dependencies (if needed)
cd infrastructure/lambda/data_sync
# ... make changes ...
pip install -r requirements.txt -t .  # If dependencies changed

# Go back to terraform directory
cd ../../terraform

# Terraform will detect changes and update Lambda
terraform plan
terraform apply
```

#### 2. Update Terraform Configuration

```bash
cd infrastructure/terraform

# Edit Terraform files (*.tf)
# ... make changes ...

# Review changes
terraform plan

# Apply changes
terraform apply
```

#### 3. Force Lambda Update

If you need to force Lambda code update (even if Terraform doesn't detect changes):

```bash
# Taint the Lambda resource (marks for recreation)
terraform taint aws_lambda_function.data_sync
terraform taint aws_lambda_function.analytics

# Plan and apply
terraform plan
terraform apply
```

Or manually update the Lambda:

```bash
# Create new zip
cd infrastructure/lambda/data_sync
zip -r ../../terraform/data_sync.zip . -x "*.pyc" "__pycache__/*"

# Update Lambda directly
aws lambda update-function-code \
    --function-name <function-name> \
    --zip-file fileb://../../terraform/data_sync.zip
```

### Importing Existing Resources

If resources already exist in AWS and you want to manage them with Terraform:

```bash
# Import resource into Terraform state
terraform import aws_s3_bucket.data_bucket <bucket-name>
terraform import aws_lambda_function.data_sync <function-name>

# Verify import
terraform plan
```

### Viewing State

```bash
# Show current state
terraform show

# Show specific resource
terraform state show aws_s3_bucket.data_bucket

# List all resources in state
terraform state list

# Move resource (rename in state)
terraform state mv aws_s3_bucket.old_name aws_s3_bucket.new_name
```

### Backend Configuration

The Terraform state is stored locally by default. For production, consider using remote state:

**S3 Backend Example** (`backend.tf`):
```hcl
terraform {
  backend "s3" {
    bucket = "my-terraform-state-bucket"
    key    = "rearc-data-pipeline/terraform.tfstate"
    region = "us-east-1"
    
    # Optional: Enable state locking with DynamoDB
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

To migrate to remote state:
```bash
# Add backend configuration to backend.tf
# Then reinitialize
terraform init -migrate-state
```

---

## Troubleshooting

### Common Issues

#### 1. Lambda Deployment Fails (Package Too Large)

**Issue**: Analytics Lambda package exceeds 50MB limit for direct upload.

**Solution**: The Terraform configuration already handles this by uploading large packages to S3 first. If you see this error, check:
- `lambda_packages` bucket exists
- IAM permissions allow S3 upload
- Package is being uploaded correctly

#### 2. Lambda Function Timeout

**Issue**: Lambda function times out before completing.

**Solution**:
- Increase `lambda_timeout` in `terraform.tfvars` (max 900 seconds)
- Check CloudWatch logs for errors
- Optimize code performance

```hcl
lambda_timeout = 600  # 10 minutes
```

#### 3. BLS Data Sync Fails (403 Forbidden)

**Issue**: Getting 403 errors when fetching BLS data.

**Solution**: Ensure User-Agent header is set correctly. Check `src/rearc/data_sync/bls.py`:
```python
USER_AGENT = "RearcDataQuest/1.0 (Contact: your-email@example.com)"
```

Update with your contact information.

#### 4. SQS Messages Not Triggering Analytics Lambda

**Issue**: Population data is saved, but Analytics Lambda doesn't run.

**Solution**:
- Check S3 bucket notifications are configured
- Verify SQS queue policy allows S3 to send messages
- Check Lambda event source mapping is enabled
- Review CloudWatch logs for errors

```bash
# Check S3 notifications
aws s3api get-bucket-notification-configuration --bucket <bucket-name>

# Check SQS queue
aws sqs get-queue-attributes --queue-url <queue-url> --attribute-names All

# Check Lambda event source mapping
aws lambda list-event-source-mappings --function-name <function-name>
```

#### 5. Terraform State Lock

**Issue**: `Error: Error acquiring the state lock`

**Solution**: Another Terraform process is running, or previous run crashed.

```bash
# Force unlock (use with caution!)
terraform force-unlock <lock-id>

# Check for stale locks in remote backend
# (if using S3 backend with DynamoDB locking)
```

#### 6. Import Errors

**Issue**: Resources exist but Terraform can't import them.

**Solution**: Ensure resource IDs match exactly. Use AWS CLI to verify:

```bash
# List existing resources
aws lambda list-functions --query "Functions[?FunctionName=='<name>'].FunctionName"
aws s3 ls | grep <bucket-name>
```

#### 7. Lambda Dependencies Missing

**Issue**: Lambda function fails with import errors.

**Solution**: Reinstall dependencies with correct platform:

```bash
# For Analytics Lambda
cd infrastructure/lambda/analytics
rm -rf *  # Clean existing (be careful!)
# Reinstall as per Step 1 instructions
```

### Debugging Tips

#### Enable Detailed Logging

```python
# In Lambda functions, use:
import logging
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
```

#### Test Locally

```bash
# Test BLS sync locally
python -m rearc.cli sync-bls <bucket-name>

# Test population fetch locally
python -m rearc.cli fetch-population <bucket-name>

# Test analytics queries (use notebook)
jupyter notebook notebooks/data_analysis.ipynb
```

#### Check CloudWatch Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/<function-name> --follow

# Get recent logs
aws logs tail /aws/lambda/<function-name> --since 1h

# Search logs
aws logs filter-log-events \
    --log-group-name /aws/lambda/<function-name> \
    --filter-pattern "ERROR"
```

#### Validate Terraform Configuration

```bash
# Format code
terraform fmt

# Validate syntax
terraform validate

# Check for security issues (if using tfsec)
tfsec .
```

---

## Additional Resources

- **Terraform Documentation**: https://www.terraform.io/docs
- **AWS Lambda Documentation**: https://docs.aws.amazon.com/lambda/
- **S3 Documentation**: https://docs.aws.amazon.com/s3/
- **EventBridge Documentation**: https://docs.aws.amazon.com/eventbridge/
- **SQS Documentation**: https://docs.aws.amazon.com/sqs/

---

## Summary

This deployment guide provides:

1. ✅ **S3 Bucket Information**: How to get and share the bucket link
2. ✅ **Architecture Overview**: Detailed component architecture
3. ✅ **Code Implementation**: Explanation of what each component does
4. ✅ **Infrastructure Deployment**: Step-by-step deployment instructions
5. ✅ **Terraform Management**: How to update, refresh, and manage infrastructure
6. ✅ **Troubleshooting**: Common issues and solutions

For questions or issues, refer to the CloudWatch logs and Terraform state outputs.

