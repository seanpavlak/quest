# Rearc Data Quest - Implementation Plan

## Overview
This plan breaks down the 4-part data pipeline quest into actionable steps. The goal is to build a complete data pipeline that sources data, processes it, analyzes it, and automates everything with AWS infrastructure.

---

## Part 1: AWS S3 & Sourcing Datasets

### Objectives
- Republish BLS dataset to S3
- Create sync script that handles updates, additions, and deletions
- Avoid duplicate uploads

### Implementation Steps

1. **Setup AWS S3 Bucket**
   - Create S3 bucket for BLS data
   - Configure appropriate bucket policies and permissions
   - Document bucket name and region

2. **Create BLS Data Sync Script**
   - Use Python with `boto3` for S3 operations
   - Use `requests` library with proper User-Agent header (to avoid 403 errors)
   - Implement recursive directory traversal of BLS source URL
   - Compare local/remote file checksums (ETags or MD5) to avoid duplicate uploads
   - Handle file additions, updates, and deletions
   - Log all operations for debugging

3. **Key Requirements**
   - User-Agent header must include contact information (per BLS policy)
   - Script should discover files dynamically (no hardcoded names)
   - Track file state to prevent re-uploading unchanged files
   - Handle S3 object deletion for removed source files

4. **Deliverables**
   - Python script: `sync_bls_data.py`
   - S3 bucket link with public read access (or shared access)
   - Documentation on how to run the script

---

## Part 2: APIs

### Objectives
- Fetch data from DataUSA API
- Save JSON response to S3

### Implementation Steps

1. **Create API Fetch Script**
   - Use Python `requests` library
   - Fetch from: `https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population`
   - Handle API errors and retries
   - Validate JSON response

2. **Save to S3**
   - Upload JSON to same or separate S3 bucket
   - Use consistent naming convention (e.g., `population_data_YYYYMMDD.json` or `population_data_latest.json`)
   - Include timestamp in filename or metadata

3. **Deliverables**
   - Python script: `fetch_population_api.py`
   - JSON file in S3

---

## Part 3: Data Analytics

### Objectives
- Load CSV and JSON as dataframes
- Perform 3 analytical queries
- Generate Jupyter notebook with results

### Implementation Steps

1. **Setup Environment**
   - Create Jupyter notebook: `data_analysis.ipynb`
   - Install required libraries: pandas, boto3, jupyter
   - Consider using PySpark if data is large (though Pandas should work for this dataset)

2. **Data Loading**
   - Load `pr.data.0.Current` CSV from S3 into dataframe
   - Load population JSON from S3 into dataframe
   - Perform data cleaning:
     - Trim whitespaces from string columns
     - Handle missing values
     - Ensure proper data types (year as int, value as float, etc.)

3. **Query 1: Population Statistics (2013-2018)**
   - Filter population data for years 2013-2018 (inclusive)
   - Calculate mean of annual US population
   - Calculate standard deviation of annual US population
   - Display results clearly

4. **Query 2: Best Year per Series ID**
   - Group time-series data by `series_id` and `year`
   - Sum `value` for all quarters per year per series
   - Find the year with maximum sum for each series_id
   - Generate report: `series_id | year | value` (summed value for that year)

5. **Query 3: Combined Report (PRS30006032 Q01 + Population)**
   - Filter time-series for `series_id = PRS30006032` and `period = Q01`
   - Join with population data on `year`
   - Generate report: `series_id | year | period | value | Population`
   - Handle cases where population data might not be available for a year

6. **Deliverables**
   - Jupyter notebook: `data_analysis.ipynb`
   - All queries with results displayed
   - Clear markdown explanations for each analysis

---

## Part 4: Infrastructure as Code & Data Pipeline

### Objectives
- Automate Parts 1 & 2 with scheduled Lambda
- Trigger analytics Lambda via SQS when JSON file is written
- Use Terraform for infrastructure provisioning

### Implementation Steps

1. **Choose IaC Tool**
   - **Using: Terraform** (HashiCorp Configuration Language - HCL)
   - Install Terraform (>= 1.0)
   - Configure AWS provider with credentials

2. **Infrastructure Components**

   **a. S3 Bucket(s)**
   - Bucket for BLS data
   - Bucket for population JSON (or same bucket with prefixes)
   - Enable versioning (optional but recommended)
   - Configure S3 event notifications for JSON file writes

   **b. IAM Roles & Policies**
   - Lambda execution role with S3 read/write permissions
   - Lambda execution role with SQS send/receive permissions
   - CloudWatch Logs permissions for Lambda

   **c. Lambda Function 1: Data Sync (Parts 1 & 2)**
   - Combine BLS sync and API fetch scripts
   - Package dependencies (boto3, requests)
   - Environment variables for:
     - S3 bucket name
     - BLS source URL
     - DataUSA API URL
   - Scheduled via EventBridge (CloudWatch Events) to run daily

   **d. SQS Queue**
   - Standard queue (or FIFO if ordering matters)
   - Configured to receive messages from S3 event notifications
   - Dead-letter queue for failed messages (optional but recommended)

   **e. Lambda Function 2: Analytics (Part 3)**
   - Triggered by SQS messages
   - Loads data from S3
   - Executes all 3 analytical queries
   - Logs results to CloudWatch Logs
   - Handles SQS message deletion after successful processing

3. **S3 Event Notification Setup**
   - Configure S3 bucket notification to send message to SQS when:
     - Object is created (PUT)
     - Object key matches pattern (e.g., `population_data_*.json`)

4. **Terraform Structure**
   ```
   part4_infrastructure/
   ├── terraform/
   │   ├── main.tf              # Main configuration
   │   ├── variables.tf         # Input variables
   │   ├── outputs.tf           # Output values
   │   ├── providers.tf         # AWS provider configuration
   │   ├── s3.tf                # S3 bucket resources
   │   ├── iam.tf               # IAM roles and policies
   │   ├── lambda.tf            # Lambda functions
   │   ├── sqs.tf               # SQS queue resources
   │   ├── eventbridge.tf       # EventBridge/CloudWatch Events
   │   ├── s3_notifications.tf  # S3 event notifications
   │   └── terraform.tfvars     # Variable values (gitignored)
   └── lambda_functions/
       ├── data_sync/
       │   ├── lambda_function.py
       │   └── requirements.txt
       └── analytics/
           ├── lambda_function.py
           └── requirements.txt
   ```

5. **Lambda Function Details**

   **Data Sync Lambda:**
   - Imports and executes BLS sync logic
   - Imports and executes API fetch logic
   - Error handling and logging
   - Returns success/failure status

   **Analytics Lambda:**
   - Receives SQS event
   - Extracts S3 object key from SQS message
   - Downloads data from S3
   - Executes all 3 queries
   - Logs results (can use structured logging)
   - Returns success/failure

6. **Terraform Resources to Create**

   **providers.tf:**
   - AWS provider configuration
   - Region specification
   - Version constraints

   **variables.tf:**
   - `project_name` - Name prefix for resources
   - `aws_region` - AWS region
   - `bls_source_url` - BLS data source URL
   - `datausa_api_url` - DataUSA API URL
   - `lambda_timeout` - Lambda function timeout
   - `lambda_memory` - Lambda function memory

   **s3.tf:**
   - S3 bucket for data storage
   - Bucket versioning
   - Bucket encryption
   - Public access block settings

   **iam.tf:**
   - IAM role for data sync Lambda
   - IAM role for analytics Lambda
   - IAM policies for S3 access
   - IAM policies for SQS access
   - IAM policies for CloudWatch Logs

   **lambda.tf:**
   - Lambda function for data sync (Parts 1 & 2)
   - Lambda function for analytics (Part 3)
   - Lambda layer for dependencies (optional)
   - Environment variables
   - Timeout and memory settings

   **sqs.tf:**
   - SQS queue for S3 event notifications
   - Dead-letter queue (optional)
   - Queue visibility timeout
   - Message retention period

   **eventbridge.tf:**
   - EventBridge rule for daily schedule
   - EventBridge target (data sync Lambda)
   - Cron expression (daily at specific time)

   **s3_notifications.tf:**
   - S3 bucket notification configuration
   - SQS queue as notification destination
   - Event filter (JSON file pattern)

   **main.tf:**
   - Data sources (if needed)
   - Local values
   - Resource tags

   **outputs.tf:**
   - S3 bucket name
   - Lambda function names/ARNs
   - SQS queue URL
   - CloudWatch Log Group names

7. **Lambda Packaging**
   - Use `archive_file` data source or `null_resource` with local-exec
   - Create ZIP files for Lambda deployment packages
   - Include Python dependencies (boto3, requests, pandas)
   - Consider using Lambda layers for common dependencies

8. **Testing**
   - Test Lambda functions locally
   - Run `terraform plan` to review changes
   - Deploy with `terraform apply`
   - Verify:
     - Scheduled trigger works (EventBridge)
     - S3 events trigger SQS
     - SQS triggers analytics Lambda
     - CloudWatch Logs contain expected output
   - Use `terraform destroy` to clean up (when needed)

9. **Deliverables**
   - Terraform configuration files
   - Lambda function code
   - `terraform.tfvars.example` (template without sensitive data)
   - Deployment instructions (README)
   - Architecture diagram (optional but helpful)

---

## Project Structure

```
rearc/
├── README.md
├── PLAN.md
├── part1_bls_sync/
│   ├── sync_bls_data.py
│   └── requirements.txt
├── part2_api_fetch/
│   ├── fetch_population_api.py
│   └── requirements.txt
├── part3_analytics/
│   ├── data_analysis.ipynb
│   └── requirements.txt
├── part4_infrastructure/
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── providers.tf
│   │   ├── s3.tf
│   │   ├── iam.tf
│   │   ├── lambda.tf
│   │   ├── sqs.tf
│   │   ├── eventbridge.tf
│   │   ├── s3_notifications.tf
│   │   └── terraform.tfvars.example
│   ├── lambda_functions/
│   │   ├── data_sync/
│   │   │   ├── lambda_function.py
│   │   │   └── requirements.txt
│   │   └── analytics/
│   │       ├── lambda_function.py
│   │       └── requirements.txt
│   └── README.md
└── docs/
    └── ARCHITECTURE.md         # Optional architecture documentation
```

---

## Implementation Order

1. **Part 1** - Get BLS data syncing to S3
2. **Part 2** - Get API data fetching working
3. **Part 3** - Develop and test analytics locally
4. **Part 4** - Integrate everything into automated pipeline

---

## Key Considerations

### Error Handling
- All scripts should have robust error handling
- Log errors to CloudWatch or local logs
- Implement retry logic for API calls and S3 operations

### Security
- Use IAM roles with least privilege
- Store sensitive config in environment variables or AWS Secrets Manager
- Don't hardcode credentials

### Cost Optimization
- Use appropriate S3 storage classes
- Consider Lambda timeout and memory settings
- Monitor CloudWatch metrics

### Testing
- Test each component independently
- Test the full pipeline end-to-end
- Handle edge cases (empty datasets, missing years, etc.)

### Terraform-Specific Considerations
- Use `terraform fmt` to format code
- Use `terraform validate` before applying
- Store state file in S3 backend (recommended for production)
- Use `.tfvars` files for environment-specific values
- Add `.terraform/` and `*.tfstate*` to `.gitignore`
- Use `terraform workspace` for multiple environments (dev/staging/prod)
- Consider using `terraform_remote_state` data source if splitting into modules

---

## Next Steps

1. Review this plan
2. Set up AWS account and credentials
3. Start with Part 1 implementation
4. Iterate through each part
5. Document as you go

