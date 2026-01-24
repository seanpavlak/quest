# GitHub OIDC Identity Provider
resource "aws_iam_openid_connect_provider" "github" {
  count = var.enable_github_oidc ? 1 : 0

  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1", # GitHub OIDC (primary)
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd", # GitHub OIDC (backup)
    "1b511abead01c8f4e08938dc4b0d25b64e643b2c"  # GitHub OIDC (2023+)
  ]

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-github-oidc"
    }
  )
}

# IAM Role for GitHub Actions
resource "aws_iam_role" "github_actions" {
  count = var.enable_github_oidc ? 1 : 0

  name = "${var.project_name}-github-actions-role"  # Shared across environments

  # Note: Condition block removed to debug "Request ARN is invalid".
  # If assume works without it, the :aud or :sub check was failing—add back and test each.
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = aws_iam_openid_connect_provider.github[0].arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
      }
    ]
  })

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-github-actions"
    }
  )
}

# IAM Policy for GitHub Actions (Terraform permissions)
resource "aws_iam_role_policy" "github_actions" {
  count = var.enable_github_oidc ? 1 : 0

  name = "${var.project_name}-github-actions-terraform-policy"  # Shared across environments
  role = aws_iam_role.github_actions[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 Permissions (for data bucket and Terraform state)
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket",
          "s3:GetBucketLocation",
          "s3:CreateBucket",
          "s3:PutBucketVersioning",
          "s3:GetBucketVersioning",
          "s3:PutBucketEncryption",
          "s3:GetBucketEncryption",
          "s3:PutBucketPublicAccessBlock",
          "s3:GetBucketPublicAccessBlock",
          "s3:PutBucketPolicy",
          "s3:GetBucketPolicy",
          "s3:DeleteBucketPolicy",
          "s3:PutLifecycleConfiguration",
          "s3:GetLifecycleConfiguration"
        ]
        Resource = [
          aws_s3_bucket.data_bucket.arn,
          "${aws_s3_bucket.data_bucket.arn}/*",
          "arn:aws:s3:::terraform-state-*",
          "arn:aws:s3:::terraform-state-*/*",
          "arn:aws:s3:::${var.project_name}-lambda-packages-*",
          "arn:aws:s3:::${var.project_name}-lambda-packages-*/*"
        ]
      },
      # Lambda Permissions
      {
        Effect = "Allow"
        Action = [
          "lambda:CreateFunction",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:GetFunction",
          "lambda:DeleteFunction",
          "lambda:AddPermission",
          "lambda:RemovePermission",
          "lambda:ListFunctions",
          "lambda:InvokeFunction",
          "lambda:GetFunctionConfiguration",
          "lambda:TagResource",
          "lambda:UntagResource",
          "lambda:ListTags"
        ]
        Resource = [
          aws_lambda_function.data_sync.arn,
          aws_lambda_function.analytics.arn,
          "arn:aws:lambda:${var.aws_region}:*:function:${var.project_name}-*-*"  # Support environment-specific functions
        ]
      },
      # IAM Permissions (for Lambda roles and policies)
      {
        Effect = "Allow"
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:PassRole",
          "iam:TagRole",
          "iam:UntagRole",
          "iam:ListRoleTags",
          "iam:UpdateAssumeRolePolicy",
          "iam:CreateServiceLinkedRole"
        ]
        Resource = [
          aws_iam_role.data_sync_lambda.arn,
          aws_iam_role.analytics_lambda.arn,
          aws_iam_role.s3_notifications.arn,
          "arn:aws:iam::*:role/${var.project_name}-*-*"  # Support environment-specific roles
        ]
      },
      # EventBridge Permissions
      {
        Effect = "Allow"
        Action = [
          "events:PutRule",
          "events:DeleteRule",
          "events:DescribeRule",
          "events:ListRules",
          "events:PutTargets",
          "events:RemoveTargets",
          "events:ListTargetsByRule",
          "events:TagResource",
          "events:UntagResource",
          "events:ListTagsForResource"
        ]
        Resource = [
          "arn:aws:events:${var.aws_region}:*:rule/${var.project_name}-*-*"  # Support environment-specific rules
        ]
      },
      # SQS Permissions
      {
        Effect = "Allow"
        Action = [
          "sqs:CreateQueue",
          "sqs:DeleteQueue",
          "sqs:GetQueueAttributes",
          "sqs:SetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ListQueues",
          "sqs:TagQueue",
          "sqs:UntagQueue",
          "sqs:ListQueueTags",
          "sqs:GetQueueAttributes",
          "sqs:ReceiveMessage",
          "sqs:SendMessage"
        ]
        Resource = [
          aws_sqs_queue.s3_notifications.arn,
          "arn:aws:sqs:${var.aws_region}:*:${var.project_name}-*"
        ]
      },
      # CloudWatch Logs Permissions
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:DeleteLogGroup",
          "logs:DescribeLogGroups",
          "logs:PutRetentionPolicy",
          "logs:TagLogGroup",
          "logs:UntagLogGroup",
          "logs:ListTagsLogGroup"
        ]
        Resource = [
          aws_cloudwatch_log_group.data_sync.arn,
          aws_cloudwatch_log_group.analytics.arn,
          "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-*-*"  # Support environment-specific log groups
        ]
      },
      # DynamoDB Permissions (for Terraform state locking)
      {
        Effect = "Allow"
        Action = [
          "dynamodb:DescribeTable",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:ListTables"
        ]
        Resource = [
          aws_dynamodb_table.terraform_state_lock.arn
        ]
      },
      # Terraform state S3 bucket permissions
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/*"
        ]
      }
    ]
  })
}
