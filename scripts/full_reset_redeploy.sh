#!/bin/bash
# Full reset: destroy all (incl. backend), apply with local state, migrate to new S3 backend. Use -y for non-interactive.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TF_DIR="$REPO_ROOT/infrastructure/terraform"
AUTO_YES=false
[[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]] && AUTO_YES=true

cd "$REPO_ROOT"

echo "=========================================="
echo "  Full AWS Reset & Redeploy"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Destroy ALL AWS resources (including S3 state bucket and DynamoDB lock table)"
echo "  2. Switch to local state and apply from scratch (creates new backend + all app resources)"
echo "  3. Migrate state to the new S3 backend"
echo "  4. Clean/reinstall Lambda deps and run smoke tests"
echo ""
if ! $AUTO_YES; then
  read -p "Continue? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
  fi
fi

echo ""
echo "=== Step 1: Full destroy (all resources including backend) ==="
cd "$TF_DIR"
terraform init -input=false

echo "Destroying all resources..."
terraform destroy -auto-approve || true

echo ""
echo "=== Step 2: Switch to local backend ==="
cp backend.tf backend.tf.bak 2>/dev/null || true

cat > backend.tf << 'LOCALBACKEND'
terraform {
  backend "local" {
    path = "terraform.tfstate"
  }
}
LOCALBACKEND

rm -rf .terraform
terraform init -reconfigure -input=false

echo ""
echo "=== Step 3: Clean and reinstall Lambda dependencies ==="
cd "$REPO_ROOT/infrastructure/lambda/analytics"
echo "Cleaning Analytics Lambda..."
rm -rf boto3 botocore requests pandas numpy pytz tzdata certifi charset_normalizer dateutil idna jmespath s3transfer urllib3 rearc *.dist-info __pycache__ bin 2>/dev/null || true

cd "$REPO_ROOT/infrastructure/lambda/data_sync"
echo "Cleaning Data Sync Lambda..."
rm -rf boto3 botocore requests *.dist-info __pycache__ bin 2>/dev/null || true

echo "Installing Analytics Lambda dependencies (Linux-compatible)..."
cd "$REPO_ROOT/infrastructure/lambda/analytics"
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: --no-cache-dir boto3 2>&1 | tail -2
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: --no-cache-dir "numpy<2.0" 2>&1 | tail -2
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: --no-cache-dir pandas 2>&1 | tail -2
mkdir -p rearc && cp -r "$REPO_ROOT/src/rearc"/* rearc/

echo "Installing Data Sync Lambda dependencies..."
cd "$REPO_ROOT/infrastructure/lambda/data_sync"
pip install -r requirements.txt -t . 2>&1 | tail -2

echo ""
echo "=== Step 4: Fresh Terraform apply (local state) ==="
cd "$TF_DIR"
terraform apply -auto-approve

echo ""
echo "=== Step 5: Migrate state to new S3 backend ==="
BUCKET=$(terraform output -raw terraform_state_bucket_name)
TABLE=$(terraform output -raw terraform_state_lock_table_name)

cat > backend.tf << S3BACKEND
terraform {
  backend "s3" {
    bucket         = "${BUCKET}"
    key            = "rearc-data-pipeline/dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "${TABLE}"
  }
}
S3BACKEND

echo "yes" | terraform init -migrate-state
rm -f terraform.tfstate terraform.tfstate.backup 2>/dev/null || true

echo ""
echo "Resources (state now in S3):"
terraform output

echo ""
echo "=== Step 6: Smoke tests ==="
echo "Invoking Data Sync Lambda..."
LAMBDA=$(terraform output -raw data_sync_lambda_function_name)
aws lambda invoke --function-name "$LAMBDA" --payload '{}' /tmp/data-sync-test.json 2>/dev/null || true
echo "Response:"
cat /tmp/data-sync-test.json 2>/dev/null | python3 -m json.tool 2>/dev/null || cat /tmp/data-sync-test.json 2>/dev/null || echo "(none)"

echo ""
echo "Waiting 15s for data sync..."
sleep 15

BUCKET_DATA=$(terraform output -raw s3_bucket_name)
echo "S3 contents:"
aws s3 ls "s3://$BUCKET_DATA/" 2>/dev/null || echo "(empty or error)"

POP=$(aws s3 ls "s3://$BUCKET_DATA/" 2>/dev/null | grep "population_data_.*\.json" | head -1 | awk '{print $4}')
if [ -n "$POP" ]; then
  echo ""
  echo "Triggering Analytics Lambda via S3 copy..."
  aws s3 cp "s3://$BUCKET_DATA/$POP" "s3://$BUCKET_DATA/population_data_clean_test_$(date +%Y%m%d_%H%M%S).json" 2>/dev/null || true
  sleep 10
  ANALYTICS_LAMBDA=$(terraform output -raw analytics_lambda_function_name)
  aws logs tail "/aws/lambda/$ANALYTICS_LAMBDA" --since 2m 2>&1 | grep -E "Query|Result|Processing" | tail -5 || true
else
  echo "No population_data_*.json yet; analytics trigger skipped."
fi

rm -f "$TF_DIR/backend.tf.bak" 2>/dev/null || true

echo ""
echo "=========================================="
echo "  Full Reset Complete"
echo "=========================================="
echo "State backend: s3://$BUCKET (key: rearc-data-pipeline/dev/terraform.tfstate)"
echo "Data bucket:  $BUCKET_DATA"
echo ""
