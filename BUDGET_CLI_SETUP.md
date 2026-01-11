# Creating AWS Budget via CLI

## Overview

AWS Budgets can be created via CLI, but requires special IAM permissions (`budgets:ModifyBudget`).

## Quick Start

```bash
./create_budget.sh
```

This will create a $100/month budget with email alerts to `seanpavlak+rearc@gmail.com`.

## If You Get Access Denied

### Option 1: Use Root Account (Easiest)

AWS Budgets can be created with root account credentials:

```bash
# Configure root account profile (one-time)
aws configure --profile root

# Run script with root profile
AWS_PROFILE=root ./create_budget.sh
```

**Note:** Root account has all permissions, so this will work immediately.

### Option 2: Add IAM Policy to Your User

1. Go to IAM Console: https://console.aws.amazon.com/iam/
2. Click "Users" → Find `rearc-data-pipeline`
3. Click "Add permissions" → "Create inline policy"
4. Click "JSON" tab and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "budgets:ModifyBudget",
        "budgets:ViewBudget",
        "budgets:CreateBudget",
        "budgets:UpdateBudget",
        "budgets:DeleteBudget",
        "budgets:DescribeBudgets",
        "budgets:DescribeBudgetNotificationsForAccount"
      ],
      "Resource": "*"
    }
  ]
}
```

5. Name it: `BudgetManagement`
6. Create policy

Then re-run:
```bash
./create_budget.sh
```

### Option 3: Manual Creation (Console)

If CLI doesn't work, create it manually:

1. Go to: https://console.aws.amazon.com/billing/home#/budgets
2. Click "Create budget"
3. Select "Cost budget"
4. Configure:
   - **Budget name:** `rearc-data-pipeline-monthly-budget`
   - **Period:** Monthly
   - **Budget amount:** $100 USD
   - **Start date:** 2024-01-01
5. Set up alerts:
   - 50% ($50) - Actual
   - 80% ($80) - Actual
   - 100% ($100) - Actual
   - 90% - Forecasted
6. Email: `seanpavlak+rearc@gmail.com`
7. Create budget

## Verify Budget Created

```bash
aws budgets describe-budgets \
  --account-id $(aws sts get-caller-identity --query Account --output text)
```

## Terraform Alternative

The Terraform configuration (`infrastructure/terraform/budget.tf`) is currently commented out due to IAM permissions. After adding the IAM policy (Option 2), you can:

1. Uncomment the resource in `budget.tf`
2. Run `terraform apply`
3. Budget will be managed by Terraform

See `infrastructure/terraform/budget_iam.tf` for an IAM policy template.

## Why CLI/API Might Fail

AWS Budgets is a sensitive service that requires special permissions. By default, only the root account can create budgets. This is by design for security (prevents accidental cost overruns).

The CLI command (`aws budgets create-budget`) requires the same permissions as Terraform, so if Terraform failed, CLI will likely fail too unless you:
- Use root account credentials
- Add the IAM policy first (Option 2)
- Use a different IAM user that has budget permissions

