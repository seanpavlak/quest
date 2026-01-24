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

The same policy is in `scripts/github-actions-terraform-policy.json` if you want to apply it via CLI (see **Alternative: Apply Steps 2 and 3 via AWS CLI**).

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
        "s3:GetBucketAcl", "s3:GetBucketCors", "s3:GetBucketWebsite",
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
        "dynamodb:DescribeTable", "dynamodb:DescribeContinuousBackups", "dynamodb:DescribeTimeToLive",
        "dynamodb:ListTagsOfResource",
        "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:ListTables"
      ],
      "Resource": ["arn:aws:dynamodb:us-east-1:851725435783:table/rearc-data-pipeline-*"]
    },
    {
      "Sid": "CloudWatchAlarms",
      "Effect": "Allow",
      "Action": [
        "cloudwatch:DescribeAlarms", "cloudwatch:PutMetricAlarm", "cloudwatch:DeleteAlarms",
        "cloudwatch:DescribeAlarmsForMetric", "cloudwatch:ListMetrics", "cloudwatch:GetMetricData",
        "cloudwatch:ListTagsForResource"
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

## Alternative: Apply Steps 2 and 3 via AWS CLI

If you prefer the CLI, you can create or update the policy and attach it in one go. The policy JSON lives in `scripts/github-actions-terraform-policy.json`.

**Prerequisites:** Step 1 done (user `github-actions-terraform` exists). AWS CLI configured with credentials that can create/update IAM policies and attach them to users.

**Option A: Run the script** (creates the policy if it doesn’t exist, or creates a new default version if it does; then attaches it to the user):

```bash
./scripts/setup-github-actions-iam.sh
```

The script uses your current AWS identity’s account ID and `AWS_REGION` (default `us-east-1`). Override with env:

```bash
AWS_ACCOUNT_ID=851725435783 AWS_REGION=us-east-1 USER_NAME=github-actions-terraform ./scripts/setup-github-actions-iam.sh
```

**Option B: Run the AWS commands yourself**

From the repo root, with `ACCOUNT` and `USER` set to your account ID and IAM user name:

```bash
ACCOUNT=851725435783
USER=github-actions-terraform
POLICY_ARN="arn:aws:iam::${ACCOUNT}:policy/GitHubActionsTerraformPolicy"
```

If the policy **does not exist**:

```bash
aws iam create-policy \
  --policy-name GitHubActionsTerraformPolicy \
  --policy-document file://scripts/github-actions-terraform-policy.json \
  --description "Terraform and CI/CD for rearc-data-pipeline (plan, apply, Lambda, S3, etc.)"
```

If the policy **already exists** (update to the latest JSON):

```bash
aws iam create-policy-version \
  --policy-arn "$POLICY_ARN" \
  --policy-document file://scripts/github-actions-terraform-policy.json \
  --set-as-default
```

Then attach it to the user:

```bash
aws iam attach-user-policy --user-name "$USER" --policy-arn "$POLICY_ARN"
```

For a different account or region, edit `scripts/github-actions-terraform-policy.json` (replace `851725435783` and `us-east-1`) before running; or use the script, which substitutes `AWS_ACCOUNT_ID` and `AWS_REGION` when set.

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

## Troubleshooting: AccessDenied During `terraform plan`

If `terraform plan` fails with **AccessDenied** for `github-actions-terraform`, the IAM policy in AWS may not match the JSON in **Step 2**. Update the `GitHubActionsTerraformPolicy` in the console so it **exactly** matches the policy above. Common missing actions:

| Error | Required action | In Step 2? |
|-------|-----------------|------------|
| `s3:GetBucketCORS` on `rearc-data-pipeline-*` | `s3:GetBucketCors` | ✅ S3 statement |
| `s3:GetBucketWebsite` on `rearc-data-pipeline-*` | `s3:GetBucketWebsite` | ✅ S3 statement |
| `dynamodb:DescribeTimeToLive` on `rearc-data-pipeline-terraform-state-lock` | `dynamodb:DescribeTimeToLive` | ✅ DynamoDB statement |
| `dynamodb:ListTagsOfResource` on `rearc-data-pipeline-terraform-state-lock` | `dynamodb:ListTagsOfResource` | ✅ DynamoDB statement |
| `cloudwatch:ListTagsForResource` on `alarm:rearc-data-pipeline-*` | `cloudwatch:ListTagsForResource` | ✅ CloudWatchAlarms statement |

**To fix:** Either run `./scripts/setup-github-actions-iam.sh` (see **Alternative: Apply Steps 2 and 3 via AWS CLI**), or in the console: IAM → **Policies** → **GitHubActionsTerraformPolicy** → **Edit** → **JSON** tab → replace with the full policy from Step 2 (or `scripts/github-actions-terraform-policy.json`) → **Save changes**. Then re-run the Terraform Plan job.

---

## If Terraform Uses a Different Backend Bucket

The policy uses `arn:aws:s3:::rearc-data-pipeline-*` (including `rearc-data-pipeline-terraform-state-*`). If your backend bucket has another prefix (e.g. from `backend.tf` or `backend_config`), add a matching `Resource` in the S3 statement, for example:

```json
"arn:aws:s3:::your-actual-backend-bucket-prefix*",
"arn:aws:s3:::your-actual-backend-bucket-prefix*/*"
```

Do the same for the DynamoDB table if its name doesn’t match `rearc-data-pipeline-*`.
