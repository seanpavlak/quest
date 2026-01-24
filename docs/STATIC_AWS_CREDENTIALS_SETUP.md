# AWS Credentials for GitHub Actions

GitHub Actions runs Terraform and sync jobs using **static AWS credentials** from repo secrets. The workflows expect `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`.

---

## Option A: rearc-data-pipeline IAM User (recommended)

The **rearc-data-pipeline** IAM user with AWS managed policies is the simplest setup. No custom policy to maintain; Terraform plan/apply and sync-outputs work without AccessDenied.

### 1. Ensure the user and policies

The **rearc-data-pipeline** user must have these **managed policies** attached:

- AmazonS3FullAccess  
- AmazonDynamoDBFullAccess  
- AmazonEventBridgeFullAccess  
- AmazonSQSFullAccess  
- AWSLambda_FullAccess  
- CloudWatchFullAccessV2  
- CloudWatchLogsFullAccess  
- IAMFullAccess  

If **rearc-data-pipeline** already exists with these, go to **2. Access key**.

Otherwise: IAM → **Users** → **Create user** (or edit **rearc-data-pipeline**) → **Add permissions** → **Attach policies directly** → attach the eight above.

### 2. Access key

1. IAM → **Users** → **rearc-data-pipeline** → **Security credentials**.
2. **Access keys** → **Create access key** (or use an existing key).
3. Copy the **Access key ID** and **Secret access key**. You won’t see the secret again.

### 3. GitHub Secrets

1. GitHub repo → **Settings** → **Secrets and variables** → **Actions**.
2. Add or update:
   - **Name:** `AWS_ACCESS_KEY_ID` → **Value:** rearc-data-pipeline access key ID  
   - **Name:** `AWS_SECRET_ACCESS_KEY` → **Value:** rearc-data-pipeline secret access key  

The **ci-cd** and **sync-outputs** workflows already use these names; no workflow edits needed.

### 4. Test

Push a commit or re-run **Terraform Plan** or **Sync Infrastructure Outputs**. The **Configure AWS credentials** step should succeed and Terraform should run without `AccessDenied`.

---

## Option B: Least-privilege (github-actions-terraform + custom policy)

For a scoped IAM user and custom policy (e.g. `rearc-data-pipeline-*` only):

1. **Create IAM user** `github-actions-terraform` (no console, API/CLI only).  
2. **Create and attach** the custom policy using the script:
   ```bash
   ./scripts/setup-github-actions-iam.sh
   ```
   Policy JSON: `scripts/github-actions-terraform-policy.json`.  
3. **Create access key** for `github-actions-terraform`.  
4. **GitHub Secrets:** set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to that user’s keys.  

Workflows stay the same; they already reference those secret names. If new Terraform AWS provider read APIs appear, you may need to add actions to the policy and re-run the script.

---

## Workflows that use these secrets

- **.github/workflows/ci-cd.yml** – plan, deploy-dev, deploy-prod  
- **.github/workflows/sync-outputs.yml** – sync-outputs-dev, sync-outputs-prod  

All use:

```yaml
aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
aws-region: ${{ env.AWS_REGION }}
```

---

## Security

- Rotate access keys periodically and if they might be exposed.  
- **rearc-data-pipeline** has broad (Full) access to S3, Lambda, IAM, etc.; protect the keys.  
- For tighter least-privilege, use **Option B** and the custom policy in `scripts/github-actions-terraform-policy.json`.
