# Rearc Data Quest

A data pipeline for syncing BLS data, fetching population data, and performing analytics.

## Project Structure

```
rearc/
├── src/
│   └── rearc/              # Main Python package
│       ├── data_sync/       # Data synchronization modules
│       │   ├── bls.py      # BLS data sync
│       │   └── population.py  # Population API fetch
│       ├── analytics/      # Analytics modules
│       │   └── queries.py  # Analytical queries
│       └── cli.py          # Command-line interface
├── notebooks/              # Jupyter notebooks
│   └── data_analysis.ipynb
├── infrastructure/         # Infrastructure as Code
│   ├── terraform/          # Terraform configuration
│   └── lambda/             # Lambda function code
│       ├── data_sync/
│       └── analytics/
├── tests/                  # Test files
├── scripts/                # Utility scripts
│   ├── test_comprehensive.sh
│   ├── test_e2e.sh
│   ├── test_local_simple.py
│   ├── clean_and_redeploy.sh
│   └── refresh_outputs.sh  # Refresh infrastructure outputs
├── docs/                   # Documentation
│   ├── DEPLOYMENT_GUIDE.md # Complete deployment guide
│   └── README.md
├── config/                 # Configuration files
│   └── outputs.json        # Infrastructure outputs (S3 bucket, Lambda ARNs, etc.)
├── data/                   # Data files (local test data)
│   └── local/              # Local test data (in .gitignore)
├── requirements.txt        # Python dependencies
└── pyproject.toml          # Python project configuration
```

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or install in development mode
pip install -e ".[dev]"
```

### Usage

#### Command Line Interface

```bash
# Sync BLS data to S3
python -m rearc.cli sync-bls <bucket-name> [--region us-east-1]

# Fetch population data
python -m rearc.cli fetch-population <bucket-name> [--region us-east-1] [--key filename.json]

# Sync both
python -m rearc.cli sync-all <bucket-name> [--region us-east-1]
```

#### Python API

```python
from rearc.data_sync import sync_bls_data, fetch_and_save_population_data

# Sync BLS data
sync_bls_data('my-bucket', region='us-east-1')

# Fetch population data
fetch_and_save_population_data('my-bucket', region='us-east-1')
```

#### Jupyter Notebook

```bash
jupyter notebook notebooks/data_analysis.ipynb
```

## Data Management & Retention

### BLS Data Sync
- **Active dataset**: The S3 bucket maintains a sync with the BLS source. Files removed from the BLS website are **archived** (not deleted) to preserve historical data.
- **Archive location**: By default, archived BLS files are moved to the `archive/` prefix in the same bucket with timestamped filenames (e.g., `archive/pr.data.0.Current_20260114_020000`).
- **Timestamped archives**: Each archive includes a timestamp to ensure uniqueness. If the same file is archived multiple times, each archive is preserved as a separate object.
- **Configuration**: Set `S3_ARCHIVE_BUCKET` and `S3_ARCHIVE_PREFIX` environment variables in the Lambda to customize archive behavior.

### Population Data
- **Historical retention**: Each API fetch creates a new timestamped JSON file (`population_data_YYYYMMDD_HHMMSS.json`). All files are retained to preserve historical data.
- **No automatic cleanup**: Population files are not automatically deleted or archived. Consider adding S3 lifecycle policies if you need to manage storage costs over time.

For more details, see the [Complete Deployment Guide](DEPLOYMENT_GUIDE.md).

## Infrastructure Deployment

See [infrastructure/README.md](infrastructure/README.md) for Terraform deployment instructions.

## Documentation

- [Complete Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Comprehensive guide with architecture, S3 bucket links, code details, and Terraform deployment instructions
- [Infrastructure Deployment](infrastructure/README.md)

## Requirements

- Python 3.9+
- AWS CLI configured
- Terraform >= 1.0 (for infrastructure)

## License

This project is part of the Rearc Data Quest assessment.
