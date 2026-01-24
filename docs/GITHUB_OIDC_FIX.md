# Fix: "Could not assume role with OIDC: Request ARN is invalid"

Use this guide when GitHub Actions fails at **Configure AWS credentials** with:

```
Error: Could not assume role with OIDC: Request ARN is invalid
```

---

## Step 1: Confirm AWS and Terraform access

1. **AWS CLI** – Ensure you can talk to the right account:
   ```bash
   aws sts get-caller-identity
   ```
   The `Account` must be **851725435783** (the one in your `role-to-assume` ARN).

2. **Terraform** – From the repo root:
   ```bash
   cd infrastructure/terraform
   terraform init -backend-config="key=rearc-data-pipeline/dev/terraform.tfstate" -reconfigure
   ```
   If this fails (e.g. backend or creds), fix that before continuing.

---

## Step 2: Check the OIDC provider in AWS

1. In **AWS Console**: IAM → **Identity providers**.
2. Find **`token.actions.githubusercontent.com`**.
   - **If it’s missing** → Terraform has not created it yet. `enable_github_oidc` may be `false`, or `terraform apply` has not been run. Go to **Step 5** and run `terraform apply`.
   - **If it exists** → Note the **Provider ARN** (e.g. `arn:aws:iam::851725435783:oidc-provider/token.actions.githubusercontent.com`). You’ll need it to match the role’s trust policy.

---

## Step 3: Check the IAM role and trust policy

1. IAM → **Roles** → search for **`rearc-data-pipeline-github-actions-role`**.
2. Open it → **Trust relationships** → **Edit trust policy** (only to inspect; we’ll change via Terraform).
3. The policy should look like this (with your account ID and provider ARN):

   - **Principal**  
     `"Federated": "arn:aws:iam::851725435783:oidc-provider/token.actions.githubusercontent.com"`

   - **Condition – audience (required):**
     ```json
     "StringEquals": {
       "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
     }
     ```

   - **Condition – subject (must match your repo):**
     ```json
     "StringLike": {
       "token.actions.githubusercontent.com:sub": "repo:seanpavlak/quest:*"
     }
     ```

4. **Frequent mistakes:**
   - `:sub` is `repo:seanpavlak/rearc:*` or `repo:rearc-data/quest:*` → should be **`repo:seanpavlak/quest:*`**.
   - Typo in repo (e.g. `sean pavlak/quest`, extra space).
   - Wrong `:aud` (must be `sts.amazonaws.com`).

   If any of these are wrong, the token from `seanpavlak/quest` will not match and you get **"Request ARN is invalid"**.

---

## Step 4: (Optional) See the OIDC token’s `sub` and `aud`

Add this **temporary** step in `.github/workflows/ci-cd.yml` in the **plan** job, **before** “Configure AWS credentials”:

```yaml
- name: Debug OIDC token
  run: |
    URL="$ACTIONS_ID_TOKEN_REQUEST_URL"
    [[ "$URL" == *"?"* ]] && URL="${URL}&audience=sts.amazonaws.com" || URL="${URL}?audience=sts.amazonaws.com"
    PAYLOAD=$(curl -s -H "Authorization: bearer $ACTIONS_ID_TOKEN_REQUEST_TOKEN" "$URL" | jq -r '.value' | cut -d. -f2 | base64 -d 2>/dev/null)
    echo "OIDC token payload: $PAYLOAD"
    echo "sub=$(echo "$PAYLOAD" | jq -r '.sub')"
    echo "aud=$(echo "$PAYLOAD" | jq -r '.aud')"
```

- `sub` should look like: `repo:seanpavlak/quest:ref:refs/heads/main` or `repo:seanpavlak/quest:pull_request` (or similar).
- `aud` should be: `sts.amazonaws.com`.

The trust policy `StringLike` value **`repo:seanpavlak/quest:*`** must match the `sub` prefix. If `sub` is for a different repo or format, we need to adjust the trust policy (or `github_repository` in Terraform) to match.

Remove this step after debugging.

---

## Step 5: Align Terraform with your repo and re-apply

1. **Repro and variables:**
   - Repo: **`seanpavlak/quest`**
   - In Terraform this is `github_repository`.

2. **Check and set `github_repository`:**
   - In `infrastructure/terraform/variables.tf`, default: `seanpavlak/quest`.
   - In `infrastructure/terraform/environments/dev.tfvars`:
     ```hcl
     github_repository = "seanpavlak/quest"
     ```
   If your repo is different, use `owner/repo` (e.g. `MyOrg/quest`).

3. **Plan and apply (dev):**
   ```bash
   cd infrastructure/terraform
   terraform plan -var-file="environments/dev.tfvars"
   ```
   - Look for changes to `aws_iam_role.github_actions` (assume role policy) or `aws_iam_openid_connect_provider.github` (thumbprints, etc.).
   - If the planned trust policy shows `repo:seanpavlak/quest:*` and the OIDC provider looks correct, apply:
     ```bash
     terraform apply -var-file="environments/dev.tfvars" -auto-approve
     ```

4. **If Terraform wants to replace or change the OIDC provider** (e.g. thumbprint or URL):
   - Review the plan. It’s normal to add a newer thumbprint; replacing the provider can change its ARN and break the role’s trust policy until Terraform updates the role as well. As long as both provider and role are in the same Terraform config, one `apply` should update both; only approve if you’re comfortable with the diff.

---

## Step 6: Re-run the GitHub Action

1. Commit and push any Terraform/config changes (or re-run the failed workflow if no code change).
2. Open the **plan** (or other) job and run it again.
3. **Configure AWS credentials** should succeed if:
   - The OIDC provider exists and has a valid thumbprint.
   - The role’s trust policy has:
     - `token.actions.githubusercontent.com:aud` = `sts.amazonaws.com`
     - `token.actions.githubusercontent.com:sub` = `repo:seanpavlak/quest:*` (or the repo you use).

---

## If it still fails

- **Request ARN is invalid:** Almost always the `sub` (or sometimes `aud`) in the OIDC token doesn’t match the trust policy. Use **Step 4** to confirm the real `sub`/`aud` and adjust `github_repository` and the trust policy.
- **InvalidIdentityToken / thumbprint:** Ensure the OIDC provider’s thumbprints in Terraform match GitHub’s current OIDC certs; we include three common thumbprints in `github_oidc.tf`.
- **Role or provider missing:** Run `terraform apply` with `enable_github_oidc = true` and `github_repository` set correctly.

---

## Trust policy pattern used in Terraform

In `github_oidc.tf`, the role’s `assume_role_policy` uses:

- `"token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"` (StringEquals)
- `"token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"` (StringLike)

For **seanpavlak/quest**, that becomes `repo:seanpavlak/quest:*`, which must match the `sub` of the OIDC token from your GitHub Actions runs.
