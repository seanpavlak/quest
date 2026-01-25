# Deployment Guide

## Architecture overview

```
EventBridge (daily 2 AM UTC) → Data Sync Lambda → S3 (BLS + population_data_*.json)
                                                         ↓
S3 notification (population_data_*.json) → SQS → Analytics Lambda → CloudWatch Logs
```

**Components:** EventBridge (`aws.eventbridge.tf`), Data Sync Lambda (`aws.lambda.tf`), S3 + notifications (`aws.buckets.tf`), SQS (`aws.sqs.tf`), Analytics Lambda (`aws.lambda.tf`), IAM (`aws.iam.tf`), Monitoring (`aws.monitoring.tf`).

---

## Outputs and bucket

- **Outputs:** `config/outputs.json` — bucket name, URLs, Lambda names, etc. View: `cat config/outputs.json`
- **Refresh after deploy:** `./scripts/refresh_outputs.sh`
- **Bucket pattern:** `{project}-{env}-data-{suffix}`; URL: `https://<bucket>.s3.<region>.amazonaws.com/`. Data bucket is publicly readable for the assignment.

---

## Deploy

### Prerequisites

- AWS CLI configured, Terraform ≥1.0, Python 3.9+

### 1. Lambda dependencies

**Data Sync:**
```bash
cd infrastructure/lambda/data_sync && pip install -r requirements.txt -t . && mkdir -p rearc && cp -r ../../../src/rearc/* rearc/
```

**Analytics** (Linux wheels for Lambda):
```bash
cd infrastructure/lambda/analytics
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: --no-cache-dir boto3 "numpy<2.0" pandas
mkdir -p rearc && cp -r ../../../src/rearc/* rearc/
```

**Or** use `./scripts/clean_and_redeploy.sh -y` or `./scripts/full_reset_redeploy.sh -y` — they install deps and deploy.

### 2. Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars   # edit if needed
terraform init
terraform plan -var-file=environments.dev.tfvars -out=tfplan
terraform apply tfplan
./scripts/refresh_outputs.sh   # or run from repo root
```

**Layout:** `main.tf`, `versions.tf`, `providers.tf`, `backend.tf`, `locals.tf`, `variables.tf`, `outputs.tf`, `aws.{backend,buckets,eventbridge,iam,lambda,monitoring,sqs}.tf`, `environments.{dev,prod}.tfvars`.

### 3. Verify

```bash
BUCKET=$(terraform output -raw s3_bucket_name)
FUNC=$(terraform output -raw data_sync_lambda_function_name)
aws s3 ls s3://$BUCKET/
aws lambda invoke --function-name $FUNC --payload '{}' /tmp/out.json && cat /tmp/out.json
```

---

## Clean deploy and reset

| Script | Use |
|--------|-----|
| `./scripts/clean_and_redeploy.sh` | Destroy app resources (keeps state backend), reinstall Lambda deps, apply, smoke test. `-y` = no prompts. |
| `./scripts/full_reset_redeploy.sh` | Destroy everything (including state backend), re-create from scratch, migrate state to new S3 backend, smoke test. `-y` = no prompts. |

After full reset: run `./scripts/refresh_outputs.sh`.

---

## Terraform operations

- **Refresh state:** `terraform plan -refresh=true` or `terraform apply -refresh-only`
- **Update after code changes:** reinstall Lambda deps if needed, then `terraform plan` / `terraform apply`
- **Force Lambda redeploy:** `terraform taint aws_lambda_function.data_sync` (or `analytics`) then `terraform apply`
- **Destroy:** `terraform destroy -var-file=environments.dev.tfvars`

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| **Lambda package too large** | Analytics is deployed via S3 (`lambda_packages` bucket). Ensure it exists and IAM allows upload. |
| **Lambda timeout** | Increase `lambda_timeout` in tfvars (max 900). Check CloudWatch logs. |
| **BLS 403** | Set `User-Agent` with contact info in `bls_parser` / BLS requests. |
| **Analytics not running** | Check S3 notifications (`population_data_*.json`), SQS policy, Lambda event source mapping, CloudWatch logs. |
| **State lock** | `terraform force-unlock <lock-id>` only if no other run is active. |
| **Import errors in Lambda** | Reinstall deps with Linux wheel: `--platform manylinux2014_x86_64 --python-version 3.12`. |

**Logs:** `aws logs tail /aws/lambda/<name> --follow`  
**Validate:** `terraform fmt` and `terraform validate`

---

## Code reference

#### Part 1: BLS Data Sync

- `src/rearc/data_sync/bls_sync.py` — recursive crawl, MD5 vs S3 ETag, deletes archived to `archive/`. Env: `S3_ARCHIVE_BUCKET`, `S3_ARCHIVE_PREFIX`.

#### Part 2: Population API Fetch

- `src/rearc/data_sync/population.py` — DataUSA API → `population_data_YYYYMMDD_HHMMSS.json`.

#### Part 3: Analytics Queries

- `src/rearc/analytics/queries.py` — `query1_population_stats`, `query2_best_year_per_series`, `query3_combined_report`.
