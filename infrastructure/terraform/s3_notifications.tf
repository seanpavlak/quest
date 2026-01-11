resource "aws_s3_bucket_notification" "json_file_notification" {
  bucket = aws_s3_bucket.data_bucket.id

  queue {
    queue_arn = aws_sqs_queue.s3_notifications.arn
    events    = ["s3:ObjectCreated:*"]
    filter_prefix = "population_data_"
    filter_suffix = ".json"
  }

  depends_on = [
    aws_sqs_queue_policy.s3_notifications
  ]
}

