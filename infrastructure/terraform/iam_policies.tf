# Separate IAM Policy for Analytics Lambda DLQ (if enabled)
# This allows the Analytics Lambda to send failed messages to DLQ

resource "aws_iam_role_policy" "analytics_lambda_dlq" {
  count = var.enable_dlq ? 1 : 0
  name  = "${local.resource_prefix}-analytics-lambda-dlq-policy"
  role  = aws_iam_role.analytics_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage"
        ]
        Resource = aws_sqs_queue.analytics_dlq[0].arn
      }
    ]
  })
}
