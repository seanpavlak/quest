# AWS Budget to limit monthly spending
# This will alert you when spending approaches your limit
# NOTE: Budgets require special IAM permissions. If this fails, create the budget manually in AWS Console.
# The budget can be created at: https://console.aws.amazon.com/billing/home#/budgets
#
# To create manually:
# 1. Go to AWS Billing Console > Budgets
# 2. Create a new budget
# 3. Budget type: Cost budget
# 4. Amount: $100
# 5. Period: Monthly
# 6. Email alerts: seanpavlak+rearc@gmail.com
# 7. Thresholds: 50%, 80%, 100% (actual) and 90% (forecasted)

# Uncomment below if your IAM user has budgets:ModifyBudget permission
# resource "aws_budgets_budget" "monthly_spend_limit" {
#   name              = "${var.project_name}-monthly-budget"
#   budget_type       = "COST"
#   limit_amount      = "100"
#   limit_unit        = "USD"
#   time_period_start = "2024-01-01_00:00"
#   time_unit         = "MONTHLY"
#
#   notification {
#     comparison_operator        = "GREATER_THAN"
#     threshold                  = 50  # Alert at 50% ($50)
#     threshold_type            = "PERCENTAGE"
#     notification_type         = "ACTUAL"
#     subscriber_email_addresses = [var.budget_alert_email]
#   }
#
#   notification {
#     comparison_operator        = "GREATER_THAN"
#     threshold                  = 80  # Alert at 80% ($80)
#     threshold_type            = "PERCENTAGE"
#     notification_type         = "ACTUAL"
#     subscriber_email_addresses = [var.budget_alert_email]
#   }
#
#   notification {
#     comparison_operator        = "GREATER_THAN"
#     threshold                  = 100  # Alert at 100% ($100)
#     threshold_type            = "PERCENTAGE"
#     notification_type         = "ACTUAL"
#     subscriber_email_addresses = [var.budget_alert_email]
#   }
#
#   notification {
#     comparison_operator        = "GREATER_THAN"
#     threshold                  = 90  # Forecast alert at 90%
#     threshold_type            = "PERCENTAGE"
#     notification_type         = "FORECASTED"
#     subscriber_email_addresses = [var.budget_alert_email]
#   }
# }
