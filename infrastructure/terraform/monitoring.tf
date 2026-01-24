# CloudWatch Alarms - Lambda errors only

resource "aws_cloudwatch_metric_alarm" "data_sync_errors" {
  alarm_name          = "${local.resource_prefix}-data-sync-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Data sync Lambda errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.data_sync.function_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "analytics_errors" {
  alarm_name          = "${local.resource_prefix}-analytics-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Analytics Lambda errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.analytics.function_name
  }

  tags = local.common_tags
}
