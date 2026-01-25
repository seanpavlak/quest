# EventBridge rule and target for daily data sync Lambda

resource "aws_cloudwatch_event_rule" "daily_schedule" {
  name                = "${local.resource_prefix}-daily-schedule"
  description         = "Trigger data sync Lambda daily"
  schedule_expression = var.schedule_expression

  tags = local.common_tags
}

resource "aws_cloudwatch_event_target" "data_sync_lambda" {
  rule      = aws_cloudwatch_event_rule.daily_schedule.name
  target_id = "DataSyncLambdaTarget"
  arn       = aws_lambda_function.data_sync.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.data_sync.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_schedule.arn
}
