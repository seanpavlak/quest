# Fix NumPy Compatibility Issue

## Problem

The Analytics Lambda is failing with:
```
ImportError: No module named 'numpy._core._multiarray_umath'
```

This happens because numpy was compiled for macOS (darwin) but Lambda runs on Linux.

Also, if you see `Killed: 9`, it means the installation process ran out of memory.

## Solution: Install Linux-Compatible Dependencies

### Option 1: Using Docker (Recommended - Most Reliable)

```bash
cd infrastructure/lambda/analytics
./install_linux_deps.sh
```

This script:
- Cleans existing macOS packages
- Uses Docker to install Linux-compatible packages
- Handles the rearc package installation

**Requirements:** Docker Desktop must be installed and running.

### Option 2: Using pip --platform Flag (No Docker Needed)

```bash
cd infrastructure/lambda/analytics
./install_without_docker.sh
```

This script:
- Cleans existing packages
- Downloads Linux wheels using pip's `--platform` flag
- Copies the rearc package manually

**Note:** This may still use significant memory, but avoids Docker.

### Option 3: Manual Step-by-Step (If Scripts Fail)

```bash
cd infrastructure/lambda/analytics

# Clean everything
rm -rf boto3 botocore requests pandas numpy pytz tzdata certifi charset_normalizer dateutil idna jmespath s3transfer urllib3 rearc *.dist-info __pycache__ bin

# Install one package at a time to avoid memory issues
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir boto3
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir pandas
pip install --platform manylinux2014_x86_64 --target . --implementation cp --python-version 3.11 --only-binary=:all: --no-cache-dir numpy

# Copy rearc package
mkdir -p rearc
cp -r ../../../../src/rearc/* rearc/
```

### Option 4: Use Lambda Layers (Alternative - Advanced)

Instead of bundling dependencies, use AWS Lambda Layers for pandas/numpy. This requires creating a Lambda Layer separately.

---

## After Fixing: Redeploy

```bash
cd infrastructure/terraform
terraform apply
```

This will rebuild the Lambda package and upload it.

---

## Verify Fix

After redeploying, check if Analytics Lambda works:

```bash
# View recent logs
aws logs tail /aws/lambda/rearc-data-pipeline-analytics --since 5m

# Or trigger manually by creating a test JSON file in S3
BUCKET=$(cd infrastructure/terraform && terraform output -raw s3_bucket_name)
aws s3 cp /tmp/test.json s3://$BUCKET/population_data_test.json
```

You should see query results instead of import errors.

---

## Troubleshooting

### "Killed: 9" Error
- **Cause:** Process ran out of memory
- **Solution:** Use Docker (Option 1) or install packages one at a time (Option 3)

### Docker Not Available
- **Solution:** Use Option 2 (pip --platform) or Option 3 (manual)

### Still Getting Import Errors
- Make sure you removed ALL existing packages before reinstalling
- Verify you're using Linux wheels (check file extensions in installed packages)
- Try the manual step-by-step approach (Option 3)

