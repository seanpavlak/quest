resource "aws_sqs_queue" "s3_notifications" {
  name                      = "${var.project_name}-s3-notifications"
  message_retention_seconds = 345600  # 4 days
  visibility_timeout_seconds = 300    # 5 minutes (should be >= Lambda timeout)

  tags = var.tags
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
            "aws:SourceArn" = "${aws_s3_bucket.data_bucket.arn}"
          }
        }
      }
    ]
  })
}

