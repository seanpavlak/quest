#!/usr/bin/env bash
#
# Create or update GitHubActionsTerraformPolicy and attach it to the
# github-actions-terraform user. Run with AWS CLI configured (profile or env)
# and privileges to create/update IAM policies and attach them to users.
#
# Prerequisites:
#   - IAM user "github-actions-terraform" exists (Step 1 in STATIC_AWS_CREDENTIALS_SETUP.md)
#   - AWS CLI installed and configured
#
# Optional env:
#   AWS_ACCOUNT_ID  – default: from `aws sts get-caller-identity`
#   AWS_REGION      – default: us-east-1 (replaces us-east-1 in the policy)
#   USER_NAME       – default: github-actions-terraform
#
# Usage:
#   ./scripts/setup-github-actions-iam.sh
#   AWS_REGION=us-west-2 ./scripts/setup-github-actions-iam.sh
#
set -euo pipefail

USER_NAME="${USER_NAME:-github-actions-terraform}"
REGION="${AWS_REGION:-us-east-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POLICY_DOC="${SCRIPT_DIR}/github-actions-terraform-policy.json"

if [[ ! -f "$POLICY_DOC" ]]; then
  echo "Error: ${POLICY_DOC} not found" >&2
  exit 1
fi

# Resolve account: explicit or from current credentials
if [[ -n "${AWS_ACCOUNT_ID:-}" ]]; then
  ACCOUNT_ID="$AWS_ACCOUNT_ID"
else
  ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
fi

POLICY_ARN="arn:aws:iam::${ACCOUNT_ID}:policy/GitHubActionsTerraformPolicy"

# Substitute account and region in the policy (so it works in any account/region)
TMP_POLICY="$(mktemp)"
trap 'rm -f "$TMP_POLICY"' EXIT
sed -e "s/851725435783/${ACCOUNT_ID}/g" -e "s/us-east-1/${REGION}/g" "$POLICY_DOC" > "$TMP_POLICY"

if aws iam get-policy --policy-arn "$POLICY_ARN" &>/dev/null; then
  echo "Updating existing policy GitHubActionsTerraformPolicy..."
  aws iam create-policy-version \
    --policy-arn "$POLICY_ARN" \
    --policy-document "file://${TMP_POLICY}" \
    --set-as-default
else
  echo "Creating policy GitHubActionsTerraformPolicy..."
  aws iam create-policy \
    --policy-name GitHubActionsTerraformPolicy \
    --policy-document "file://${TMP_POLICY}" \
    --description "Terraform and CI/CD for rearc-data-pipeline (plan, apply, Lambda, S3, etc.)"
fi

echo "Attaching policy to user ${USER_NAME}..."
aws iam attach-user-policy --user-name "$USER_NAME" --policy-arn "$POLICY_ARN"
echo "Done."
