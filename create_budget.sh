#!/bin/bash
# Create AWS Budget via CLI
# This script creates a $100/month budget with email alerts

set -e

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
EMAIL="seanpavlak+rearc@gmail.com"

echo "Creating AWS Budget..."
echo "Account ID: $ACCOUNT_ID"
echo "Budget: \$100/month"
echo "Email: $EMAIL"
echo ""

# Create the budget
BUDGET_RESULT=$(aws budgets create-budget \
  --account-id "$ACCOUNT_ID" \
  --budget "{
    \"BudgetName\": \"rearc-data-pipeline-monthly-budget\",
    \"BudgetLimit\": {
      \"Amount\": \"100\",
      \"Unit\": \"USD\"
    },
    \"TimeUnit\": \"MONTHLY\",
    \"BudgetType\": \"COST\",
    \"TimePeriod\": {
      \"Start\": \"2024-01-01T00:00:00Z\"
    }
  }" 2>&1)

if echo "$BUDGET_RESULT" | grep -q "already exists"; then
    echo "⚠️  Budget already exists. Updating instead..."
    aws budgets update-budget \
      --account-id "$ACCOUNT_ID" \
      --budget "{
        \"BudgetName\": \"rearc-data-pipeline-monthly-budget\",
        \"BudgetLimit\": {
          \"Amount\": \"100\",
          \"Unit\": \"USD\"
        },
        \"TimeUnit\": \"MONTHLY\",
        \"BudgetType\": \"COST\",
        \"TimePeriod\": {
          \"Start\": \"2024-01-01T00:00:00Z\"
        }
      }" && echo "✅ Budget updated successfully"
elif echo "$BUDGET_RESULT" | grep -q "AccessDenied"; then
    echo "❌ Error: Access Denied"
    echo ""
    echo "Your IAM user doesn't have budget permissions."
    echo ""
    echo "Option 1: Use root account credentials (temporary)"
    echo "  aws configure --profile root"
    echo "  # Then re-run this script"
    echo ""
    echo "Option 2: Attach budget policy to your IAM user"
    echo "  1. Go to: https://console.aws.amazon.com/iam/"
    echo "  2. Find user: rearc-data-pipeline"
    echo "  3. Add permissions > Attach policies directly"
    echo "  4. Create policy with this JSON:"
    echo ""
    cat << 'POLICY'
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
        "budgets:DescribeBudgets"
      ],
      "Resource": "*"
    }
  ]
}
POLICY
    echo ""
    echo "Option 3: Create budget manually in console"
    echo "  https://console.aws.amazon.com/billing/home#/budgets"
    exit 1
else
    echo "✅ Budget created successfully"
fi

echo ""
echo "Adding email notifications..."

# Function to create notification
create_notification() {
    local threshold=$1
    local notification_type=$2
    
    aws budgets create-notification \
      --account-id "$ACCOUNT_ID" \
      --budget-name "rearc-data-pipeline-monthly-budget" \
      --notification "{
        \"NotificationType\": \"$notification_type\",
        \"ComparisonOperator\": \"GREATER_THAN\",
        \"Threshold\": $threshold
      }" \
      --subscriber "{
        \"SubscriptionType\": \"EMAIL\",
        \"Address\": \"$EMAIL\"
      }" 2>&1 | grep -v "already exists" || true
}

# Create all notifications
echo "  - Alert at 50% (\$50)..."
create_notification 50 "ACTUAL"

echo "  - Alert at 80% (\$80)..."
create_notification 80 "ACTUAL"

echo "  - Alert at 100% (\$100)..."
create_notification 100 "ACTUAL"

echo "  - Forecast alert at 90%..."
create_notification 90 "FORECASTED"

echo ""
echo "✅ Budget and notifications configured!"
echo ""
echo "Check your email ($EMAIL) for confirmation messages from AWS."

