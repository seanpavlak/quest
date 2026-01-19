# CLI Usage Guide

## How to Run the CLI

### Method 1: As a Python Module (Recommended)
```bash
# From the project root
python -m rearc.cli <command> [options]

# Examples:
python -m rearc.cli sync-bls my-bucket
python -m rearc.cli fetch-population my-bucket
python -m rearc.cli sync-all my-bucket
```

### Method 2: After Installation (with entry point)
```bash
# First install the package
pip install -e .

# Then use the 'rearc' command directly
rearc sync-bls my-bucket
rearc fetch-population my-bucket
rearc sync-all my-bucket
```

### Method 3: Direct Python Execution
```bash
# From the project root with PYTHONPATH
PYTHONPATH=src python -m rearc.cli sync-bls my-bucket
```

## Available Commands

### 1. `sync-bls` - Sync BLS Data to S3
Syncs BLS time-series data from the source website to S3.

```bash
python -m rearc.cli sync-bls <bucket-name> [options]
```

**Arguments:**
- `bucket` (required): S3 bucket name
- `--region` (optional): AWS region (default: `us-east-1`)
- `--archive-bucket` (optional): Separate bucket for archived files
- `--archive-prefix` (optional): Archive prefix (default: `archive/`)

**Examples:**
```bash
# Basic sync
python -m rearc.cli sync-bls my-data-bucket

# With custom region
python -m rearc.cli sync-bls my-data-bucket --region us-west-2

# With archive configuration
python -m rearc.cli sync-bls my-data-bucket --archive-bucket my-archive-bucket --archive-prefix old-data/
```

### 2. `fetch-population` - Fetch Population Data
Fetches population data from the DataUSA API and saves to S3.

```bash
python -m rearc.cli fetch-population <bucket-name> [options]
```

**Arguments:**
- `bucket` (required): S3 bucket name
- `--region` (optional): AWS region (default: `us-east-1`)
- `--key` (optional): Custom S3 object key (default: auto-generated with timestamp)

**Examples:**
```bash
# Basic fetch
python -m rearc.cli fetch-population my-data-bucket

# With custom key
python -m rearc.cli fetch-population my-data-bucket --key population.json

# With custom region
python -m rearc.cli fetch-population my-data-bucket --region us-west-2
```

### 3. `sync-all` - Sync Both BLS and Population Data
Runs both BLS sync and population fetch in sequence.

```bash
python -m rearc.cli sync-all <bucket-name> [options]
```

**Arguments:**
- `bucket` (required): S3 bucket name
- `--region` (optional): AWS region (default: `us-east-1`)
- `--archive-bucket` (optional): Archive bucket for BLS data
- `--archive-prefix` (optional): Archive prefix (default: `archive/`)

**Examples:**
```bash
# Sync everything
python -m rearc.cli sync-all my-data-bucket

# With archive configuration
python -m rearc.cli sync-all my-data-bucket --archive-prefix backups/
```

## Prerequisites

1. **AWS Credentials**: Configured via:
   - AWS CLI: `aws configure`
   - Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - IAM role (if running on EC2)
   - AWS credentials file: `~/.aws/credentials`

2. **Python Dependencies**: Install with:
   ```bash
   pip install -r requirements.txt
   ```

3. **S3 Bucket**: Must exist and be accessible with your AWS credentials

## Error Handling

The CLI will:
- Exit with code `1` on failure
- Exit with code `130` on keyboard interrupt (Ctrl+C)
- Log detailed error messages with stack traces
- Provide helpful error messages for common issues

## Integration with Lambda

The Lambda functions use the same underlying functions (`sync_bls_data`, `fetch_and_save_population_data`) but call them directly, not through the CLI. The CLI is primarily for:
- Local development and testing
- Manual data sync operations
- Demonstrating the scripts required by Parts 1 & 2 of the quest
