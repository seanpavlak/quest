# IAM Policy for Budget Management
# This allows the IAM user to create and manage budgets

resource "aws_iam_policy" "budget_management" {
  name        = "${var.project_name}-budget-management"
  description = "Allows creating and managing AWS Budgets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "budgets:ModifyBudget",
          "budgets:ViewBudget",
          "budgets:CreateBudget",
          "budgets:UpdateBudget",
          "budgets:DeleteBudget",
          "budgets:DescribeBudgets",
          "budgets:DescribeBudgetNotificationsForAccount",
          "budgets:DescribeBudgetPerformanceHistory"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = "no-reply-aws@amazon.com"
          }
        }
      }
    ]
  })
}

# Attach the policy to the IAM user (if using a specific user)
# Uncomment and update the user name if needed
# resource "aws_iam_user_policy_attachment" "budget_policy" {
#   user       = "rearc-data-pipeline"  # Update with your IAM user name
#   policy_arn = aws_iam_policy.budget_management.arn
# }

output "budget_policy_arn" {
  description = "ARN of the budget management IAM policy"
  value       = aws_iam_policy.budget_management.arn
}

