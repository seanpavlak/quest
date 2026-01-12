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
│   ├── ARCHITECTURE.md
│   ├── DEPLOYMENT_GUIDE.md # Complete deployment guide
│   └── README.md
├── outputs.json            # Infrastructure outputs (S3 bucket, Lambda ARNs, etc.)
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

## Infrastructure Deployment

See [infrastructure/README.md](infrastructure/README.md) for Terraform deployment instructions.

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Complete Deployment Guide](docs/DEPLOYMENT_GUIDE.md) - Comprehensive guide with S3 bucket links, architecture, code details, and Terraform deployment instructions
- [Infrastructure Deployment](infrastructure/README.md)

## Requirements

- Python 3.9+
- AWS CLI configured
- Terraform >= 1.0 (for infrastructure)

## License

This project is part of the Rearc Data Quest assessment.
