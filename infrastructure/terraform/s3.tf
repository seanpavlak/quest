resource "aws_s3_bucket" "data_bucket" {
  bucket        = "${local.resource_prefix}-data-${random_id.bucket_suffix.hex}"
  force_destroy = var.environment == "dev" ? true : false # Only allow force_destroy in dev

  tags = local.common_tags
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

# S3 Bucket Ownership Controls (required for modern S3 buckets)
resource "aws_s3_bucket_ownership_controls" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  rule {
    object_ownership = "BucketOwnerEnforced" # Disables ACLs, best security practice
  }

  depends_on = [
    aws_s3_bucket_public_access_block.data_bucket
  ]
}

# Public access block - configurable via variable
# When enable_public_s3_access=true, block_public_policy is set to false so the
# public_read bucket policy can be applied. If you see "public policies are
# prevented by the BlockPublicPolicy setting", ensure S3 account-level
# "Block Public Access" does not have "Block public bucket policies" enabled.
resource "aws_s3_bucket_public_access_block" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  block_public_acls       = !var.enable_public_s3_access
  block_public_policy     = !var.enable_public_s3_access
  ignore_public_acls      = !var.enable_public_s3_access
  restrict_public_buckets = !var.enable_public_s3_access
}

# Short delay so block_public_policy=false can propagate before applying the
# public bucket policy (avoids 403 from eventual consistency).
resource "null_resource" "delay_before_public_policy" {
  count = var.enable_public_s3_access ? 1 : 0

  depends_on = [aws_s3_bucket_public_access_block.data_bucket]

  provisioner "local-exec" {
    command = "sleep 15"
  }
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

  depends_on = [null_resource.delay_before_public_policy[0]]
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
  bucket        = "${local.resource_prefix}-lambda-packages-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = local.common_tags
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

# S3 Bucket Ownership Controls for Lambda packages bucket
resource "aws_s3_bucket_ownership_controls" "lambda_packages" {
  bucket = aws_s3_bucket.lambda_packages.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }

  depends_on = [
    aws_s3_bucket_public_access_block.lambda_packages
  ]
}

# S3 Bucket Public Access Block for Lambda packages
resource "aws_s3_bucket_public_access_block" "lambda_packages" {
  bucket = aws_s3_bucket.lambda_packages.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket for Access Logs
resource "aws_s3_bucket" "access_logs" {
  bucket        = "${local.resource_prefix}-access-logs-${random_id.bucket_suffix.hex}"
  force_destroy = var.environment == "dev" ? true : false

  tags = merge(
    local.common_tags,
    {
      Purpose = "AccessLogs"
    }
  )
}

resource "aws_s3_bucket_versioning" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }

  depends_on = [
    aws_s3_bucket_public_access_block.access_logs
  ]
}

# Bucket policy required for S3 server access logging when Object Ownership is
# BucketOwnerEnforced (ACLs disabled). The logging service (logging.s3.amazonaws.com)
# must be granted s3:PutObject via bucket policy; without it, log delivery fails silently.
data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_policy" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "S3ServerAccessLogsPolicy"
        Effect    = "Allow"
        Principal = { Service = "logging.s3.amazonaws.com" }
        Action    = "s3:PutObject"
        Resource  = "${aws_s3_bucket.access_logs.arn}/*"
        Condition = {
          ArnLike      = { "aws:SourceArn" = aws_s3_bucket.data_bucket.arn }
          StringEquals = { "aws:SourceAccount" = data.aws_caller_identity.current.account_id }
        }
      }
    ]
  })

  depends_on = [aws_s3_bucket_ownership_controls.access_logs]
}

# S3 Lifecycle Configuration for access logs (auto-delete old logs after 90 days)
resource "aws_s3_bucket_lifecycle_configuration" "access_logs" {
  bucket = aws_s3_bucket.access_logs.id

  rule {
    id     = "delete_old_access_logs"
    status = "Enabled"

    filter {}

    expiration {
      days = 90 # Keep access logs for 90 days
    }

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

# S3 Bucket Access Logging for audit trails
resource "aws_s3_bucket_logging" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  target_bucket = aws_s3_bucket.access_logs.id
  target_prefix = "data-bucket/"

  depends_on = [
    aws_s3_bucket_ownership_controls.access_logs,
    aws_s3_bucket_ownership_controls.data_bucket,
    aws_s3_bucket_policy.access_logs
  ]
}

# S3 Intelligent-Tiering for production environment (cost optimization)
resource "aws_s3_bucket_intelligent_tiering_configuration" "data_bucket" {
  count  = var.environment == "prod" ? 1 : 0
  bucket = aws_s3_bucket.data_bucket.id
  name   = "EntireBucket"

  filter {
    prefix = ""
  }

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}
