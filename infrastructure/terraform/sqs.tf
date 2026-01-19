# Dead Letter Queue for Analytics Lambda
resource "aws_sqs_queue" "analytics_dlq" {
  count                     = var.enable_dlq ? 1 : 0
  name                      = "${local.resource_prefix}-analytics-dlq"
  message_retention_seconds = 1209600 # 14 days (max for DLQ)

  tags = merge(local.common_tags, {
    Purpose = "DeadLetterQueue"
  })
}

resource "aws_sqs_queue" "s3_notifications" {
  name                       = "${local.resource_prefix}-s3-notifications"
  message_retention_seconds  = var.sqs_message_retention_seconds
  visibility_timeout_seconds = var.lambda_timeout + 60 # Lambda timeout + buffer

  redrive_policy = var.enable_dlq ? jsonencode({
    deadLetterTargetArn = aws_sqs_queue.analytics_dlq[0].arn
    maxReceiveCount     = 3
  }) : null

  tags = local.common_tags
}

resource "aws_sqs_queue_policy" "s3_notifications" {
  queue_url = aws_sqs_queue.s3_notifications.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.s3_notifications.arn
        Condition = {
          ArnLike = {
            "aws:SourceArn" = aws_s3_bucket.data_bucket.arn
          }
        }
      }
    ]
  })
}

