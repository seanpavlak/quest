# Architecture Overview

## Data Pipeline Flow

```
┌─────────────────┐
│  EventBridge    │  (Daily Schedule)
│  (Cron)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda         │  Part 1: BLS Data Sync
│  (Data Sync)    │  Part 2: Population API Fetch
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  S3 Bucket      │  Stores:
│                 │  - BLS time-series data
│                 │  - Population JSON files
└────────┬────────┘
         │
         │ (JSON file created)
         ▼
┌─────────────────┐
│  S3 Event       │  Notification when JSON file
│  Notification   │  is written
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQS Queue      │  Receives S3 event messages
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Lambda         │  Part 3: Analytics
│  (Analytics)    │  - Query 1: Population stats
│                 │  - Query 2: Best year per series
│                 │  - Query 3: Combined report
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CloudWatch     │  Logs analytics results
│  Logs           │
└─────────────────┘
```

## Components

### Part 1: BLS Data Sync
- **Module**: `src/rearc/data_sync/bls.py`
- **CLI Command**: `python -m rearc.cli sync-bls <bucket>`
- **Source**: https://download.bls.gov/pub/time.series/pr/
- **Destination**: S3 bucket
- **Features**: Change detection, recursive sync, User-Agent compliance
- **Lambda**: `infrastructure/lambda/data_sync/lambda_function.py`

### Part 2: Population API Fetch
- **Module**: `src/rearc/data_sync/population.py`
- **CLI Command**: `python -m rearc.cli fetch-population <bucket>`
- **Source**: DataUSA API
- **Destination**: S3 bucket (JSON file)
- **Features**: Timestamp-based naming, error handling
- **Lambda**: `infrastructure/lambda/data_sync/lambda_function.py`

### Part 3: Data Analytics
- **Notebook**: `notebooks/data_analysis.ipynb`
- **Module**: `src/rearc/analytics/queries.py`
- **Data Sources**: S3 (BLS CSV + Population JSON)
- **Queries**: 3 analytical reports
  - Query 1: Population statistics (mean/std dev 2013-2018)
  - Query 2: Best year per series_id
  - Query 3: Combined report (PRS30006032 Q01 + population)
- **Output**: Jupyter notebook with results
- **Lambda**: `infrastructure/lambda/analytics/lambda_function.py`

### Part 4: Infrastructure Automation
- **IaC Tool**: Terraform
- **Location**: `infrastructure/terraform/`
- **Components**:
  - S3 bucket with versioning and encryption
  - IAM roles and policies
  - Lambda functions (data sync + analytics)
  - SQS queue
  - EventBridge schedule (daily cron)
  - S3 event notifications
  - CloudWatch log groups

## Security

- IAM roles with least privilege
- S3 bucket encryption (AES256)
- Public access blocked
- VPC endpoints (optional, for enhanced security)

## Monitoring

- CloudWatch Logs for Lambda functions
- CloudWatch Metrics for Lambda invocations
- SQS queue metrics
- S3 access logs (optional)

## Cost Optimization

- S3 lifecycle policies (optional)
- Lambda memory/timeout tuning
- CloudWatch log retention (7 days)
- SQS message retention (4 days)

## Repository Structure

```
rearc/
├── src/rearc/              # Python package
│   ├── data_sync/          # Data synchronization modules
│   │   ├── bls.py          # BLS data sync
│   │   └── population.py   # Population API fetch
│   ├── analytics/          # Analytics modules
│   │   └── queries.py      # Analytical queries
│   └── cli.py              # Command-line interface
├── notebooks/              # Jupyter notebooks
│   └── data_analysis.ipynb
├── infrastructure/         # Infrastructure as Code
│   ├── terraform/          # Terraform configuration
│   └── lambda/             # Lambda function code
│       ├── data_sync/
│       └── analytics/
├── tests/                  # Test files
└── docs/                   # Documentation
```

## Usage

### Command Line Interface

```bash
# Sync BLS data
python -m rearc.cli sync-bls <bucket-name> [--region us-east-1]

# Fetch population data
python -m rearc.cli fetch-population <bucket-name> [--region us-east-1]

# Sync both
python -m rearc.cli sync-all <bucket-name> [--region us-east-1]
```

### Python API

```python
from rearc.data_sync import sync_bls_data, fetch_and_save_population_data
from rearc.analytics import query1_population_stats

# Sync BLS data
sync_bls_data('my-bucket', region='us-east-1')

# Fetch population data
fetch_and_save_population_data('my-bucket', region='us-east-1')
```

### Infrastructure Deployment

```bash
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

