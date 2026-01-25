# Outputs (alphabetical)
# https://developer.hashicorp.com/terraform/language/style

output "analytics_lambda_arn" {
  description = "ARN of the analytics Lambda function"
  value       = aws_lambda_function.analytics.arn
}

output "analytics_lambda_function_name" {
  description = "Name of the analytics Lambda function"
  value       = aws_lambda_function.analytics.function_name
}

output "cloudwatch_log_group_analytics" {
  description = "CloudWatch Log Group for analytics Lambda"
  value       = aws_cloudwatch_log_group.analytics.name
}

output "cloudwatch_log_group_data_sync" {
  description = "CloudWatch Log Group for data sync Lambda"
  value       = aws_cloudwatch_log_group.data_sync.name
}

output "data_sync_lambda_arn" {
  description = "ARN of the data sync Lambda function"
  value       = aws_lambda_function.data_sync.arn
}

output "data_sync_lambda_function_name" {
  description = "Name of the data sync Lambda function"
  value       = aws_lambda_function.data_sync.function_name
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.data_bucket.arn
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for data storage"
  value       = aws_s3_bucket.data_bucket.id
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.s3_notifications.arn
}

output "sqs_queue_url" {
  description = "URL of the SQS queue"
  value       = aws_sqs_queue.s3_notifications.id
}

output "terraform_state_bucket_arn" {
  description = "ARN of the S3 bucket for Terraform state storage"
  value       = aws_s3_bucket.terraform_state.arn
}

output "terraform_state_bucket_name" {
  description = "Name of the S3 bucket for Terraform state storage"
  value       = aws_s3_bucket.terraform_state.id
}

output "terraform_state_lock_table_arn" {
  description = "ARN of the DynamoDB table for Terraform state locking"
  value       = aws_dynamodb_table.terraform_state_lock.arn
}

output "terraform_state_lock_table_name" {
  description = "Name of the DynamoDB table for Terraform state locking"
  value       = aws_dynamodb_table.terraform_state_lock.name
}
