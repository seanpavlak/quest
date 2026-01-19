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
  name              = "/aws/lambda/${local.resource_prefix}-data-sync"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

resource "aws_cloudwatch_log_group" "analytics" {
  name              = "/aws/lambda/${local.resource_prefix}-analytics"
  retention_in_days = var.log_retention_days

  tags = local.common_tags
}

# Data Sync Lambda Function
resource "aws_lambda_function" "data_sync" {
  filename         = data.archive_file.data_sync_zip.output_path
  function_name    = "${local.resource_prefix}-data-sync"
  role             = aws_iam_role.data_sync_lambda.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.data_sync_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory

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

  tags = local.common_tags
}

# Upload Analytics Lambda package to S3 (required for large packages >70MB)
resource "aws_s3_object" "analytics_lambda_package" {
  bucket = aws_s3_bucket.lambda_packages.id
  key    = "analytics-${data.archive_file.analytics_zip.output_base64sha256}.zip"
  source = data.archive_file.analytics_zip.output_path
  etag   = data.archive_file.analytics_zip.output_base64sha256
}

# Analytics Lambda Function (using S3 for large package)
resource "aws_lambda_function" "analytics" {
  s3_bucket        = aws_s3_bucket.lambda_packages.id
  s3_key           = aws_s3_object.analytics_lambda_package.key
  function_name    = "${local.resource_prefix}-analytics"
  role             = aws_iam_role.analytics_lambda.arn
  handler          = "lambda_function.lambda_handler"
  source_code_hash = data.archive_file.analytics_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory

  environment {
    variables = {
      S3_BUCKET_NAME = aws_s3_bucket.data_bucket.id
    }
  }

  dynamic "dead_letter_config" {
    for_each = var.enable_dlq ? [1] : []
    content {
      target_arn = aws_sqs_queue.analytics_dlq[0].arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.analytics,
    aws_iam_role_policy.analytics_lambda,
    aws_s3_object.analytics_lambda_package
  ]

  tags = local.common_tags
}

# SQS Event Source Mapping for Analytics Lambda
resource "aws_lambda_event_source_mapping" "analytics_sqs" {
  event_source_arn = aws_sqs_queue.s3_notifications.arn
  function_name    = aws_lambda_function.analytics.arn
  batch_size       = 1
  enabled          = true
}

