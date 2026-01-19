# CloudWatch Alarms for Lambda Monitoring

# Alarm for Data Sync Lambda errors
resource "aws_cloudwatch_metric_alarm" "data_sync_errors" {
  alarm_name          = "${local.resource_prefix}-data-sync-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "This metric monitors data sync lambda errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.data_sync.function_name
  }

  tags = local.common_tags
}

# Alarm for Analytics Lambda errors
resource "aws_cloudwatch_metric_alarm" "analytics_errors" {
  alarm_name          = "${local.resource_prefix}-analytics-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "This metric monitors analytics lambda errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.analytics.function_name
  }

  tags = local.common_tags
}

# Alarm for SQS queue depth (if messages are backing up)
resource "aws_cloudwatch_metric_alarm" "sqs_queue_depth" {
  alarm_name          = "${local.resource_prefix}-sqs-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 10
  alarm_description   = "This metric monitors SQS queue depth"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.s3_notifications.name
  }

  tags = local.common_tags
}

# Alarm for DLQ messages (if enabled)
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  count = var.enable_dlq ? 1 : 0

  alarm_name          = "${local.resource_prefix}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "This metric monitors dead letter queue messages"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.analytics_dlq[0].name
  }

  tags = local.common_tags
}
