# Rearc Data Quest - Submission

**Candidate:** Sean Pavlak  
**Date:** January 2026  
**Repository:** [GitHub Repository](https://github.com/seanpavlak/quest)

---

## Summary

Complete implementation of all four parts with automated AWS pipeline:
- **Part 1**: BLS data sync to S3
- **Part 2**: Population API integration
- **Part 3**: Three analytical queries (notebook + Lambda)
- **Part 4**: Terraform infrastructure with CI/CD

Pipeline runs nightly at 2 AM UTC.

---

## Part 1: AWS S3 & Sourcing Datasets ✅

**S3 Links:**
- Bucket: https://rearc-data-pipeline-dev-data-fe445231.s3.us-east-1.amazonaws.com/
- Main BLS File: https://rearc-data-pipeline-dev-data-fe445231.s3.us-east-1.amazonaws.com/pr.data.0.Current

**Code:**
- [`src/rearc/data_sync/bls_sync.py`](src/rearc/data_sync/bls_sync.py)
- [`infrastructure/lambda/data_sync/lambda_function.py`](infrastructure/lambda/data_sync/lambda_function.py)

**Features:** Dynamic file discovery, content-based change detection, BLS policy compliance (User-Agent header)

---

## Part 2: APIs ✅

**Code:**
- [`src/rearc/data_sync/population.py`](src/rearc/data_sync/population.py)

**S3 Files:** `population_data_YYYYMMDD_HHMMSS.json` in same bucket as Part 1

**API:** https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population

---

## Part 3: Data Analytics ✅

**Notebook:** [`notebooks/data_analysis.ipynb`](notebooks/data_analysis.ipynb)

**Code:**
- [`src/rearc/analytics/queries.py`](src/rearc/analytics/queries.py)
- [`infrastructure/lambda/analytics/lambda_function.py`](infrastructure/lambda/analytics/lambda_function.py)

**Latest Results (Jan 26, 2026):**
- **Query 1**: Mean = 322,069,808, Std Dev = 4,158,441
- **Query 2**: 282 records (best year per series)
- **Query 3**: 31 records (10 with population data)

---

## Part 4: Infrastructure as Code ✅

**Terraform:** [`infrastructure/terraform/`](infrastructure/terraform/)

**Architecture:**
```
EventBridge (daily 2 AM UTC) → Data Sync Lambda → S3
S3 Notification → SQS → Analytics Lambda → CloudWatch Logs
```

**Resources:**
- S3: `rearc-data-pipeline-dev-data-fe445231`
- Lambdas: `rearc-data-pipeline-dev-data-sync`, `rearc-data-pipeline-dev-analytics`
- SQS: `rearc-data-pipeline-dev-s3-notifications`
- EventBridge: `rearc-data-pipeline-dev-daily-schedule`

**CI/CD:** [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)

---

## Verification

**S3 Data:**
```bash
aws s3 ls s3://rearc-data-pipeline-dev-data-fe445231/
```

**Analytics Results:**
```bash
python3 scripts/view_analytics_results.py
```

**Infrastructure:**
```bash
cat config/outputs.json
```

**CloudWatch Logs:**
- `/aws/lambda/rearc-data-pipeline-dev-data-sync`
- `/aws/lambda/rearc-data-pipeline-dev-analytics`

---

## Additional Features

- Test suite (`tests/`)
- CLI tool (`src/rearc/cli.py`)
- Environment separation (dev/prod)
- CloudWatch monitoring
- Comprehensive documentation
