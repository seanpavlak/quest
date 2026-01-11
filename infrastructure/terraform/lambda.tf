# Archive Lambda function code
data "archive_file" "data_sync_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/data_sync"
  output_path = "${path.module}/data_sync.zip"
  excludes    = ["__pycache__", "*.pyc", "requirements.txt"]
}

data "archive_file" "analytics_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/analytics"
  output_path = "${path.module}/analytics.zip"
  excludes    = ["__pycache__", "*.pyc", "requirements.txt"]
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "data_sync" {
  name              = "/aws/lambda/${var.project_name}-data-sync"
  retention_in_days = 7

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "analytics" {
  name              = "/aws/lambda/${var.project_name}-analytics"
  retention_in_days = 7

  tags = var.tags
}

# Data Sync Lambda Function
resource "aws_lambda_function" "data_sync" {
  filename         = data.archive_file.data_sync_zip.output_path
  function_name    = "${var.project_name}-data-sync"
  role            = aws_iam_role.data_sync_lambda.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.data_sync_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory

  environment {
    variables = {
      S3_BUCKET_NAME  = aws_s3_bucket.data_bucket.id
      BLS_SOURCE_URL  = var.bls_source_url
      DATAUSA_API_URL = var.datausa_api_url
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.data_sync,
    aws_iam_role_policy.data_sync_lambda
  ]

  tags = var.tags
}

# Analytics Lambda Function
resource "aws_lambda_function" "analytics" {
  filename         = data.archive_file.analytics_zip.output_path
  function_name    = "${var.project_name}-analytics"
  role            = aws_iam_role.analytics_lambda.arn
  handler         = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.analytics_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = var.lambda_timeout
  memory_size     = var.lambda_memory

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.data_bucket.id
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.analytics,
    aws_iam_role_policy.analytics_lambda
  ]

  tags = var.tags
}

# SQS Event Source Mapping for Analytics Lambda
resource "aws_lambda_event_source_mapping" "analytics_sqs" {
  event_source_arn = aws_sqs_queue.s3_notifications.arn
  function_name    = aws_lambda_function.analytics.arn
  batch_size       = 1
  enabled          = true
}

