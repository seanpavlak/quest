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
├── docs/                   # Documentation
│   └── ARCHITECTURE.md
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Python project configuration
└── PLAN.md                 # Implementation plan
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

- [Implementation Plan](PLAN.md)
- [Architecture Overview](docs/ARCHITECTURE.md)

## Requirements

- Python 3.9+
- AWS CLI configured
- Terraform >= 1.0 (for infrastructure)

## License

This project is part of the Rearc Data Quest assessment.
