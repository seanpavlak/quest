# Step-by-Step: Static AWS Credentials for GitHub Actions

Use this guide when OIDC fails with **"Request ARN is invalid"** and you need to run Terraform Plan and Deploy from GitHub Actions using static AWS credentials instead.

---

## Prerequisites

- Access to the **AWS account** (851725435783) as a user with rights to create IAM users and policies
- **Terraform has been applied at least once** so the S3 backend, DynamoDB table, and other resources exist (or you will create the IAM user after the first apply from your own machine)

---

## Step 1: Create an IAM User

1. In the **AWS Console**, go to **IAM** → **Users** → **Create user**.
2. **User name:** `github-actions-terraform` (or any name you prefer).
3. Leave **"Provide user access to the AWS Management Console"** unchecked (credentials are for API/CLI only).
4. Click **Next**.
5. On **Set permissions**, choose **Attach policies directly** — do **not** add any policy yet. Click **Next**.
6. Review and **Create user**.

---

## Step 2: Create a Custom Policy for Terraform

1. Go to **IAM** → **Policies** → **Create policy**.
2. Open the **JSON** tab and replace the contents with the policy below.
3. Replace `851725435783` with your AWS account ID if it’s different.
4. Replace `us-east-1` with your `aws_region` if you use another region.
5. Click **Next**.
6. **Policy name:** `GitHubActionsTerraformPolicy`.
7. **Description:** `Terraform and CI/CD for rearc-data-pipeline (plan, apply, Lambda, S3, etc.).`
8. **Create policy**.

**Policy JSON:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetBucketLocation",
        "s3:GetBucketAcl",
        "s3:CreateBucket", "s3:PutBucketVersioning", "s3:GetBucketVersioning",
        "s3:PutEncryptionConfiguration", "s3:GetEncryptionConfiguration",
        "s3:PutBucketPublicAccessBlock", "s3:GetBucketPublicAccessBlock",
        "s3:PutBucketPolicy", "s3:GetBucketPolicy", "s3:DeleteBucketPolicy",
        "s3:PutLifecycleConfiguration", "s3:GetLifecycleConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::rearc-data-pipeline-*",
        "arn:aws:s3:::rearc-data-pipeline-*/*"
      ]
    },
    {
      "Sid": "Lambda",
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction", "lambda:UpdateFunctionCode", "lambda:UpdateFunctionConfiguration",
        "lambda:GetFunction", "lambda:DeleteFunction", "lambda:AddPermission", "lambda:RemovePermission",
        "lambda:ListFunctions", "lambda:InvokeFunction", "lambda:GetFunctionConfiguration",
        "lambda:TagResource", "lambda:UntagResource", "lambda:ListTags"
      ],
      "Resource": ["arn:aws:lambda:us-east-1:851725435783:function:rearc-data-pipeline-*"]
    },
    {
      "Sid": "IAM",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole", "iam:DeleteRole", "iam:GetRole", "iam:AttachRolePolicy", "iam:DetachRolePolicy",
        "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:GetRolePolicy", "iam:ListRolePolicies",
        "iam:ListAttachedRolePolicies", "iam:PassRole", "iam:TagRole", "iam:UntagRole", "iam:ListRoleTags",
        "iam:UpdateAssumeRolePolicy", "iam:CreateServiceLinkedRole",
        "iam:GetOpenIDConnectProvider"
      ],
      "Resource": [
        "arn:aws:iam::851725435783:role/rearc-data-pipeline-*",
        "arn:aws:iam::851725435783:oidc-provider/*"
      ]
    },
    {
      "Sid": "EventBridge",
      "Effect": "Allow",
      "Action": [
        "events:PutRule", "events:DeleteRule", "events:DescribeRule", "events:ListRules",
        "events:PutTargets", "events:RemoveTargets", "events:ListTargetsByRule",
        "events:TagResource", "events:UntagResource", "events:ListTagsForResource"
      ],
      "Resource": ["arn:aws:events:us-east-1:851725435783:rule/rearc-data-pipeline-*"]
    },
    {
      "Sid": "SQS",
      "Effect": "Allow",
      "Action": [
        "sqs:CreateQueue", "sqs:DeleteQueue", "sqs:GetQueueAttributes", "sqs:SetQueueAttributes",
        "sqs:GetQueueUrl", "sqs:ListQueues", "sqs:TagQueue", "sqs:UntagQueue", "sqs:ListQueueTags",
        "sqs:ReceiveMessage", "sqs:SendMessage"
      ],
      "Resource": ["arn:aws:sqs:us-east-1:851725435783:rearc-data-pipeline-*"]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy", "logs:TagLogGroup", "logs:UntagLogGroup", "logs:ListTagsForResource"
      ],
      "Resource": [
        "arn:aws:logs:us-east-1:851725435783:log-group:/aws/lambda/rearc-data-pipeline-*",
        "arn:aws:logs:us-east-1:851725435783:log-group:*"
      ]
    },
    {
      "Sid": "DynamoDB",
      "Effect": "Allow",
      "Action": [
        "dynamodb:DescribeTable", "dynamodb:DescribeContinuousBackups", "dynamodb:GetItem", "dynamodb:PutItem",
        "dynamodb:DeleteItem", "dynamodb:ListTables"
      ],
      "Resource": ["arn:aws:dynamodb:us-east-1:851725435783:table/rearc-data-pipeline-*"]
    },
    {
      "Sid": "CloudWatchAlarms",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:DescribeAlarms", "cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarmsForMetric", "cloudwatch:ListMetrics", "cloudwatch:GetMetricData"
      ],
      "Resource": ["arn:aws:cloudwatch:us-east-1:851725435783:alarm:rearc-data-pipeline-*"]
    }
  ]
}
```

---

## Step 3: Attach the Policy to the User

1. Go to **IAM** → **Users** → open **github-actions-terraform**.
2. **Permissions** tab → **Add permissions** → **Attach policies directly**.
3. Search for **GitHubActionsTerraformPolicy**, select it, and **Add permissions**.

---

## Step 4: Create Access Keys

1. On the **github-actions-terraform** user page, open the **Security credentials** tab.
2. **Access keys** → **Create access key**.
3. Use **Application running outside AWS** (or **Command Line Interface**). **Next**.
4. (Optional) add a description; **Create access key**.
5. **Copy** the **Access key ID** and **Secret access key** and store them somewhere safe. You won’t see the secret again.

---

## Step 5: Add GitHub Secrets

1. Open your repo on **GitHub** → **Settings** → **Secrets and variables** → **Actions**.
2. **New repository secret**:
   - **Name:** `AWS_ACCESS_KEY_ID`  
   - **Value:** the access key ID from Step 4.
3. **New repository secret**:
   - **Name:** `AWS_SECRET_ACCESS_KEY`  
   - **Value:** the secret access key from Step 4.

---

## Step 6: Update the GitHub Actions Workflow

Edit `.github/workflows/ci-cd.yml` and change the **Configure AWS credentials** step in all three jobs that use AWS: **plan**, **deploy-dev**, and **deploy-prod**.

### 6a. Plan job

Find:

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::851725435783:role:rearc-data-pipeline-github-actions-role
          aws-region: ${{ env.AWS_REGION }}
          role-session-name: GitHubActions-Terraform-Plan
```

Replace with:

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
```

### 6b. Deploy-dev job

Find:

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::851725435783:role:rearc-data-pipeline-github-actions-role
          aws-region: ${{ env.AWS_REGION }}
          role-session-name: GitHubActions-Terraform-Deploy
```

Replace with:

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
```

### 6c. Deploy-prod job

Find:

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::851725435783:role:rearc-data-pipeline-github-actions-role
          aws-region: ${{ env.AWS_REGION }}
          role-session-name: GitHubActions-Terraform-Deploy-Prod
```

Replace with:

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
```

(You can also remove the `id-token: write` permission from the **plan**, **deploy-dev**, and **deploy-prod** jobs if you’re no longer using OIDC; it’s optional and doesn’t affect static credentials.)

---

## Step 7: Commit, Push, and Test

1. Commit the workflow changes and push to the branch that runs the **Terraform Plan** (e.g. open a PR to `main`/`master`).
2. In **Actions**, run or re-run the **Terraform Plan** workflow.
3. Confirm the **Configure AWS credentials** step succeeds and the rest of the job (Terraform init, plan, etc.) runs.

---

## Optional: Revert to OIDC Later

If you fix OIDC (e.g. after an AWS support case or config changes):

1. In the three jobs, change the **Configure AWS credentials** step back to use `role-to-assume` and `role-session-name` instead of `aws-access-key-id` and `aws-secret-access-key`.
2. You can leave or remove the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets; they won’t be used once `role-to-assume` is set.
3. Ensure `id-token: write` is set for **plan**, **deploy-dev**, and **deploy-prod** when using OIDC.

---

## Security Notes

- **Rotate keys** on a schedule and if they might be exposed.
- Prefer **OIDC** when it works; static keys are a workaround.
- Restrict the IAM policy to the minimum needed; the JSON above is scoped to `rearc-data-pipeline-*` and related resources.

---

## If Terraform Uses a Different Backend Bucket

The policy uses `arn:aws:s3:::terraform-state-*` and `arn:aws:s3:::rearc-data-pipeline-*`. If your backend bucket has another prefix (e.g. from `backend.tf` or `backend_config`), add a matching `Resource` in the S3 statement, for example:

```json
"arn:aws:s3:::your-actual-backend-bucket-prefix*",
"arn:aws:s3:::your-actual-backend-bucket-prefix*/*"
```

Do the same for the DynamoDB table if its name doesn’t match `rearc-data-pipeline-*`.
