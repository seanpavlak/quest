# AWS Budget Setup - Limit Monthly Spending

## Overview

AWS Budgets allows you to set spending limits and receive alerts. **Important:** AWS Budgets can alert you, but **cannot automatically stop services** to prevent overage. You'll need to monitor and take action.

## Option 1: Using Terraform (Recommended)

I've added a budget configuration to your Terraform setup.

### Step 1: Add Your Email to terraform.tfvars

```bash
cd infrastructure/terraform
```

Edit `terraform.tfvars` and add:
```hcl
budget_alert_email = "your-email@example.com"
```

### Step 2: Apply the Budget

```bash
terraform apply
```

This will create:
- Monthly budget limit: $100
- Alerts at: $50 (50%), $80 (80%), $100 (100%)
- Forecast alert: When forecasted to exceed $90

## Option 2: Using AWS Console (Quick Setup)

1. Go to AWS Billing Dashboard
2. Click "Budgets" in left menu
3. Click "Create budget"
4. Choose "Cost budget"
5. Set:
   - Budget name: `Monthly-Spend-Limit`
   - Period: Monthly
   - Budget amount: $100
6. Configure alerts:
   - Alert 1: 50% of budgeted amount ($50)
   - Alert 2: 80% of budgeted amount ($80)
   - Alert 3: 100% of budgeted amount ($100)
   - Alert 4: Forecasted to exceed 90%
7. Add your email address
8. Create budget

## Option 3: Using AWS CLI

```bash
# Create budget JSON file
cat > budget.json << 'EOF'
{
  "BudgetName": "Monthly-Spend-Limit",
  "BudgetLimit": {
    "Amount": "100",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST",
  "CostFilters": {},
  "CostTypes": {
    "IncludeTax": true,
    "IncludeSubscription": true,
    "UseBlended": false,
    "IncludeRefund": false,
    "IncludeCredit": false,
    "IncludeUpfront": true,
    "IncludeRecurring": true,
    "IncludeOtherSubscription": true,
    "IncludeSupport": true,
    "IncludeDiscount": true,
    "UseAmortized": false
  }
}
EOF

# Create budget
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json \
  --notifications-with-subscribers \
    '[{"Notification":{"NotificationType":"ACTUAL","ComparisonOperator":"GREATER_THAN","Threshold":50,"ThresholdType":"PERCENTAGE"},"Subscribers":[{"SubscriptionType":"EMAIL","Address":"your-email@example.com"}]}]'
```

## Important Limitations

⚠️ **AWS Budgets CANNOT automatically stop services**

AWS Budgets will:
- ✅ Alert you via email
- ✅ Show spending in dashboard
- ✅ Forecast future spending

AWS Budgets will NOT:
- ❌ Automatically stop EC2 instances
- ❌ Automatically delete S3 buckets
- ❌ Automatically terminate Lambda functions
- ❌ Prevent charges from continuing

## What You Need to Do

1. **Set up alerts** (using one of the methods above)
2. **Monitor your email** for budget alerts
3. **Take action** when you receive alerts:
   - Review AWS Cost Explorer
   - Identify what's costing money
   - Stop/delete resources if needed
   - Use `terraform destroy` to remove infrastructure

## Additional Protection: AWS Cost Anomaly Detection

You can also set up Cost Anomaly Detection:

```bash
aws ce create-anomaly-detector \
  --anomaly-detector-name "Spending-Anomalies" \
  --monitor-type "DIMENSIONAL"
```

## Estimated Monthly Costs for This Project

Based on your current setup:
- **S3 Storage**: ~$0.0001/month (1.5MB)
- **S3 Requests**: ~$0.0001/month (minimal)
- **Lambda Invocations**: ~$0.20/month (daily runs)
- **Lambda Compute**: ~$0.10/month (execution time)
- **CloudWatch Logs**: ~$0.50/month (log storage)
- **SQS**: ~$0.00/month (within free tier)
- **EventBridge**: ~$0.00/month (within free tier)

**Total Estimated: < $1/month**

You're well under $100, but it's still good practice to set up alerts!

## Quick Check Current Spending

```bash
# Check current month's costs
aws ce get-cost-and-usage \
  --time-period Start=$(date -u +%Y-%m-01),End=$(date -u +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --query 'ResultsByTime[0].Total.BlendedCost.Amount' \
  --output text
```

## Emergency: Stop All Resources

If you need to stop everything immediately:

```bash
cd infrastructure/terraform
terraform destroy
```

This will delete all resources and stop all charges.

