#!/bin/bash
#
# Script to refresh outputs.json from Terraform outputs
# This captures all infrastructure outputs at the repo level for easy access
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"
OUTPUTS_FILE="$PROJECT_ROOT/outputs.json"

echo "Refreshing outputs.json from Terraform..."
echo ""

# Check if terraform directory exists
if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Error: Terraform directory not found: $TERRAFORM_DIR"
    exit 1
fi

# Check if terraform is initialized
if [ ! -f "$TERRAFORM_DIR/.terraform/terraform.tfstate" ] && [ ! -f "$TERRAFORM_DIR/terraform.tfstate" ]; then
    echo "Error: Terraform not initialized. Run 'terraform init' first."
    exit 1
fi

# Change to terraform directory
cd "$TERRAFORM_DIR"

# Get terraform outputs in JSON format
echo "Fetching Terraform outputs..."
OUTPUTS_JSON=$(terraform output -json 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$OUTPUTS_JSON" ]; then
    echo "Error: Failed to get Terraform outputs. Make sure Terraform is initialized and deployed."
    exit 1
fi

# Extract values and build simplified JSON
echo "Processing outputs..."
SIMPLIFIED_JSON=$(echo "$OUTPUTS_JSON" | python3 -c "
import sys
import json

try:
    data = json.load(sys.stdin)
    # Extract values
    values = {k: v['value'] for k, v in data.items() if 'value' in v}
    
    # Extract bucket name and region
    bucket_name = values.get('s3_bucket_name', '')
    region = 'us-east-1'  # Default region, could be extracted from ARN if needed
    
    # Build enhanced output
    output = {
        's3_bucket_name': bucket_name,
        's3_bucket_arn': values.get('s3_bucket_arn', ''),
        's3_bucket_url': f'https://{bucket_name}.s3.{region}.amazonaws.com' if bucket_name else '',
        's3_bucket_region': region,
        'data_sync_lambda_function_name': values.get('data_sync_lambda_function_name', ''),
        'data_sync_lambda_arn': values.get('data_sync_lambda_arn', ''),
        'analytics_lambda_function_name': values.get('analytics_lambda_function_name', ''),
        'analytics_lambda_arn': values.get('analytics_lambda_arn', ''),
        'sqs_queue_url': values.get('sqs_queue_url', ''),
        'sqs_queue_arn': values.get('sqs_queue_arn', ''),
        'cloudwatch_log_group_data_sync': values.get('cloudwatch_log_group_data_sync', ''),
        'cloudwatch_log_group_analytics': values.get('cloudwatch_log_group_analytics', ''),
    }
    
    # Add example URLs if bucket name exists
    if bucket_name:
        output['example_urls'] = {
            'bucket_root': f'https://{bucket_name}.s3.{region}.amazonaws.com/',
            'bls_main_file': f'https://{bucket_name}.s3.{region}.amazonaws.com/pr.data.0.Current',
            'population_data_pattern': f'https://{bucket_name}.s3.{region}.amazonaws.com/population_data_*.json'
        }
    
    print(json.dumps(output, indent=2))
except Exception as e:
    print(f'Error processing outputs: {e}', file=sys.stderr)
    sys.exit(1)
")

if [ $? -ne 0 ] || [ -z "$SIMPLIFIED_JSON" ]; then
    echo "Error: Failed to process outputs."
    exit 1
fi

# Write to outputs.json
echo "$SIMPLIFIED_JSON" > "$OUTPUTS_FILE"

echo "✅ Successfully updated $OUTPUTS_FILE"
echo ""
echo "Current S3 Bucket:"
BUCKET_NAME=$(echo "$SIMPLIFIED_JSON" | python3 -c "import sys, json; print(json.load(sys.stdin)['s3_bucket_name'])" 2>/dev/null)
if [ -n "$BUCKET_NAME" ]; then
    echo "  Name: $BUCKET_NAME"
    echo "  URL:  https://${BUCKET_NAME}.s3.us-east-1.amazonaws.com/"
else
    echo "  (not found)"
fi
echo ""

