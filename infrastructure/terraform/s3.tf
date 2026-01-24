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

# Allow public read for the assignment ("share with us a link")
resource "aws_s3_bucket_public_access_block" "data_bucket" {
  bucket = aws_s3_bucket.data_bucket.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "public_read" {
  bucket = aws_s3_bucket.data_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadGetObject"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.data_bucket.arn}/*"
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.data_bucket]
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

