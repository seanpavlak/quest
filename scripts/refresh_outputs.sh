#!/bin/bash
# Refresh config/outputs.json from Terraform outputs.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"
CONFIG_DIR="$PROJECT_ROOT/config"
OUTPUTS_FILE="$CONFIG_DIR/outputs.json"

echo "Refreshing outputs.json from Terraform..."
echo ""

mkdir -p "$CONFIG_DIR"
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Error: Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

if [ ! -d "$TERRAFORM_DIR/.terraform" ]; then
    echo "Error: Terraform not initialized. Run 'terraform init' first."
    exit 1
fi

cd "$TERRAFORM_DIR"
echo "Fetching Terraform outputs..."
terraform output -json 2>/dev/null | python3 "$PROJECT_ROOT/scripts/terraform_outputs_to_json.py" --output "$OUTPUTS_FILE" -e dev

if [ $? -ne 0 ]; then
    echo "Error: Failed to get or process Terraform outputs. Make sure Terraform is initialized and deployed."
    exit 1
fi

echo "✅ Successfully updated $OUTPUTS_FILE"
echo ""
echo "Current S3 Bucket:"
BUCKET_NAME=$(python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d.get('s3_bucket_name',''))" "$OUTPUTS_FILE" 2>/dev/null)
if [ -n "$BUCKET_NAME" ]; then
    echo "  Name: $BUCKET_NAME"
    echo "  URL:  https://${BUCKET_NAME}.s3.us-east-1.amazonaws.com/"
else
    echo "  (not found)"
fi
echo ""

