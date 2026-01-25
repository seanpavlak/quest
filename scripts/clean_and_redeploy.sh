#!/bin/bash
# Clean deploy: destroy non-backend resources, reinstall deps, redeploy, test.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AUTO_YES=false
[[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]] && AUTO_YES=true

cd "$REPO_ROOT"

echo "=========================================="
echo "  Clean Deployment Script"
echo "=========================================="
echo ""
echo "This will:"
echo "  1. Destroy all AWS resources (except the Terraform state backend: S3 bucket and DynamoDB lock table)"
echo "  2. Clean local Lambda dependencies"
echo "  3. Reinstall dependencies (Linux-compatible)"
echo "  4. Redeploy everything"
echo "  5. Test end-to-end"
echo ""
if ! $AUTO_YES; then
  read -p "Continue? (yes/no): " confirm
  if [ "$confirm" != "yes" ]; then
    echo "Aborted."
    exit 1
  fi
fi

echo ""
echo "=== Step 1: Destroying All AWS Resources (excluding backend state bucket and DynamoDB lock table) ==="
cd infrastructure/terraform

terraform init -input=false
# Exclude backend (S3 state bucket + DynamoDB lock) so destroy doesn't break follow-up plan/apply.
BACKEND_PATTERN='^random_id\.state_bucket_suffix$|^aws_s3_bucket\.terraform_state$|^aws_s3_bucket_versioning\.terraform_state$|^aws_s3_bucket_server_side_encryption_configuration\.terraform_state$|^aws_s3_bucket_public_access_block\.terraform_state$|^aws_s3_bucket_ownership_controls\.terraform_state$|^aws_s3_bucket_lifecycle_configuration\.terraform_state$|^aws_dynamodb_table\.terraform_state_lock$'

state_list=$(terraform state list) || { echo "Error: terraform state list failed (is the backend reachable?)."; exit 1; }
targets=()
while IFS= read -r r; do
  [ -n "$r" ] && targets+=(-target="$r")
done < <(echo "$state_list" | grep -v -E "$BACKEND_PATTERN" || true)

if [ ${#targets[@]} -eq 0 ]; then
  echo "No non-backend resources in state; skipping destroy."
else
  terraform destroy -auto-approve "${targets[@]}"
fi

echo ""
echo "=== Step 2: Cleaning Local Lambda Dependencies ==="
cd ../lambda/analytics
echo "Cleaning Analytics Lambda..."
rm -rf boto3 botocore requests pandas numpy pytz tzdata certifi charset_normalizer dateutil idna jmespath s3transfer urllib3 rearc *.dist-info __pycache__ bin 2>/dev/null || true
echo "✓ Analytics Lambda cleaned"

cd ../data_sync
echo "Cleaning Data Sync Lambda..."
rm -rf boto3 botocore requests *.dist-info __pycache__ bin 2>/dev/null || true
echo "✓ Data Sync Lambda cleaned"

echo ""
echo "=== Step 3: Reinstalling Lambda Dependencies ==="
echo ""
echo "Installing Analytics Lambda dependencies (Linux-compatible)..."
cd ../analytics
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: --no-cache-dir boto3 2>&1 | tail -2
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: --no-cache-dir "numpy<2.0" 2>&1 | tail -2
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.12 --only-binary=:all: --no-cache-dir pandas 2>&1 | tail -2

echo "Copying rearc package..."
mkdir -p rearc
cp -r "$REPO_ROOT/src/rearc"/* rearc/
echo "✓ Analytics Lambda dependencies installed"

echo ""
echo "Installing Data Sync Lambda dependencies..."
cd ../data_sync
pip install -r requirements.txt -t . 2>&1 | tail -2
echo "✓ Data Sync Lambda dependencies installed"

echo ""
echo "=== Step 4: Fresh Terraform Deployment ==="
cd ../../terraform

echo "Initializing Terraform..."
terraform init

echo ""
echo "Planning deployment..."
terraform plan -out=tfplan

echo ""
if ! $AUTO_YES; then
  read -p "Review plan above. Deploy? (yes/no): " deploy_confirm
  if [ "$deploy_confirm" != "yes" ]; then
    echo "Deployment aborted."
    exit 1
  fi
fi

echo ""
echo "Deploying..."
terraform apply tfplan

echo ""
echo "=== Step 5: Verifying Deployment ==="
echo ""
echo "Resources created:"
terraform output

echo ""
echo "=== Step 6: Testing Data Sync Lambda ==="
LAMBDA=$(terraform output -raw data_sync_lambda_function_name)
echo "Invoking Data Sync Lambda..."
aws lambda invoke --function-name $LAMBDA --payload '{}' /tmp/data-sync-test.json
echo "Response:"
cat /tmp/data-sync-test.json | python3 -m json.tool 2>/dev/null || cat /tmp/data-sync-test.json

echo ""
echo "Waiting 10 seconds for data to sync..."
sleep 10

echo ""
echo "Checking S3 bucket..."
BUCKET=$(terraform output -raw s3_bucket_name)
aws s3 ls s3://$BUCKET/

echo ""
echo "=== Step 7: Testing Analytics Lambda ==="
echo "Creating test population file to trigger Analytics Lambda..."
aws s3 cp s3://$BUCKET/population_data_20260111_204633.json s3://$BUCKET/population_data_clean_test_$(date +%Y%m%d_%H%M%S).json 2>&1 | tail -1

echo ""
echo "Waiting 10 seconds for Analytics Lambda to process..."
sleep 10

echo ""
echo "Analytics Lambda logs:"
ANALYTICS_LAMBDA=$(terraform output -raw analytics_lambda_function_name)
aws logs tail /aws/lambda/$ANALYTICS_LAMBDA --since 2m 2>&1 | grep -E "Query|Result|Processing" | tail -10

echo ""
echo "=========================================="
echo "  Clean Deployment Complete!"
echo "=========================================="
echo ""
echo "✅ All resources deployed"
echo "✅ Budget configured with: seanpavlak+rearc@gmail.com"
echo "✅ Data Sync Lambda tested"
echo "✅ Analytics Lambda tested"
echo ""
echo "S3 Bucket: $BUCKET"
echo "URL: https://$BUCKET.s3.amazonaws.com/"

