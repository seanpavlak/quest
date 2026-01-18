resource "aws_s3_bucket" "data_bucket" {
  bucket = "${var.project_name}-data-${random_id.bucket_suffix.hex}"

  tags = var.tags
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_s3_bucket_versioning" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Public access block - configurable via variable
resource "aws_s3_bucket_public_access_block" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  block_public_acls       = !var.enable_public_s3_access
  block_public_policy     = !var.enable_public_s3_access
  ignore_public_acls      = !var.enable_public_s3_access
  restrict_public_buckets = !var.enable_public_s3_access
}

# Bucket policy to allow public read access (only if enabled)
resource "aws_s3_bucket_policy" "public_read" {
  count  = var.enable_public_s3_access ? 1 : 0
  bucket = aws_s3_bucket.data_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.data_bucket.arn}/*"
      }
    ]
  })

  depends_on = [aws_s3_bucket_public_access_block.data_bucket]
}

# S3 Lifecycle Configuration for cost optimization
resource "aws_s3_bucket_lifecycle_configuration" "data_bucket" {
  count  = var.s3_lifecycle_enabled ? 1 : 0
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    id     = "delete_old_incomplete_multipart_uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "transition_old_versions"
    status = "Enabled"

    filter {}

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_transition {
      noncurrent_days = 90
      storage_class   = "GLACIER"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }
}

# S3 Bucket for Lambda deployment packages
resource "aws_s3_bucket" "lambda_packages" {
  bucket = "${var.project_name}-lambda-packages-${random_id.bucket_suffix.hex}"

  tags = var.tags
}

resource "aws_s3_bucket_versioning" "lambda_packages" {
  bucket = aws_s3_bucket.lambda_packages.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lambda_packages" {
  bucket = aws_s3_bucket.lambda_packages.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

