# End-to-End Testing Guide

## Overview

This guide walks you through testing the entire data pipeline from start to finish, verifying all 4 parts work together.

## Prerequisites

- AWS CLI configured
- Terraform deployed (all resources created)
- Access to AWS Console (optional, for visual verification)

---

## Test 1: Manual Data Sync Lambda Trigger

### Step 1: Trigger Data Sync Lambda

```bash
cd infrastructure/terraform

# Get Lambda function name
LAMBDA_NAME=$(terraform output -raw data_sync_lambda_function_name)

# Invoke the Lambda manually
aws lambda invoke \
  --function-name $LAMBDA_NAME \
  --payload '{}' \
  /tmp/lambda-response.json

# Check response
cat /tmp/lambda-response.json | python3 -m json.tool
```

**Expected Result:**
```json
{
  "statusCode": 200,
  "body": {
    "bls_sync": true,
    "population_fetch": true
  }
}
```

### Step 2: Verify Data in S3

```bash
# Get bucket name
BUCKET=$(terraform output -raw s3_bucket_name)

# List all files
aws s3 ls s3://$BUCKET/ --recursive

# Check specific files
aws s3 ls s3://$BUCKET/ | grep "pr.data.0.Current"
aws s3 ls s3://$BUCKET/ | grep "population_data"
```

**Expected Result:**
- `pr.data.0.Current` - BLS data file (~1.5MB)
- `population_data_YYYYMMDD_HHMMSS.json` - Population data file

### Step 3: Check Data Sync Lambda Logs

```bash
# View recent logs
aws logs tail /aws/lambda/$LAMBDA_NAME --since 10m

# Or follow logs in real-time
aws logs tail /aws/lambda/$LAMBDA_NAME --follow
```

**Expected Logs:**
- "Starting BLS data sync..."
- "Discovered X files from source"
- "Uploaded: pr.data.0.Current"
- "Starting population data fetch..."
- "Saved data to s3://..."

---

## Test 2: Verify Analytics Lambda Trigger

### Step 1: Check SQS Queue

```bash
# Get queue URL
QUEUE_URL=$(terraform output -raw sqs_queue_url)

# Check for messages
aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages
```

**Expected:** Messages should appear when population JSON file is created

### Step 2: Trigger Analytics Lambda (by creating new population file)

```bash
BUCKET=$(terraform output -raw s3_bucket_name)

# Copy existing population file to trigger S3 event
aws s3 cp \
  s3://$BUCKET/population_data_20260111_204633.json \
  s3://$BUCKET/population_data_test_$(date +%Y%m%d_%H%M%S).json
```

**This will:**
1. Create new file in S3
2. S3 sends notification to SQS
3. SQS triggers Analytics Lambda
4. Analytics Lambda processes queries

### Step 3: Check Analytics Lambda Logs

```bash
ANALYTICS_LAMBDA=$(terraform output -raw analytics_lambda_function_name)

# Wait a few seconds for processing
sleep 5

# Check logs
aws logs tail /aws/lambda/$ANALYTICS_LAMBDA --since 5m
```

**Expected Logs:**
- "Processing S3 object: s3://..."
- "Query 1 Results: {'mean': ..., 'std_dev': ...}"
- "Query 2 Results: X records"
- "Query 3 Results: X records"

---

## Test 3: Verify EventBridge Schedule

### Step 1: Check Schedule Status

```bash
RULE_NAME="rearc-data-pipeline-daily-schedule"

# Check if rule exists and is enabled
aws events describe-rule --name $RULE_NAME

# List targets
aws events list-targets-by-rule --rule $RULE_NAME
```

**Expected:**
- State: ENABLED
- Schedule: `cron(0 2 * * ? *)` (daily at 2 AM UTC)
- Target: Data Sync Lambda

### Step 2: Test Schedule Manually (Optional)

You can manually trigger the schedule:

```bash
# Get rule name
RULE_NAME="rearc-data-pipeline-daily-schedule"

# Manually trigger the rule
aws events put-events \
  --entries '[{
    "Source": "manual.test",
    "DetailType": "Manual Trigger",
    "Detail": "{\"test\": true}"
  }]'
```

Or wait for the scheduled time (2 AM UTC).

---

## Test 4: Complete End-to-End Flow

### Full Test Script

```bash
#!/bin/bash
# Complete end-to-end test

cd infrastructure/terraform

echo "=== End-to-End Pipeline Test ==="
echo ""

# Get resource names
BUCKET=$(terraform output -raw s3_bucket_name)
DATA_SYNC_LAMBDA=$(terraform output -raw data_sync_lambda_function_name)
ANALYTICS_LAMBDA=$(terraform output -raw analytics_lambda_function_name)
QUEUE_URL=$(terraform output -raw sqs_queue_url)

echo "1. Triggering Data Sync Lambda..."
aws lambda invoke \
  --function-name $DATA_SYNC_LAMBDA \
  --payload '{}' \
  /tmp/data-sync-response.json

echo "   Response:"
cat /tmp/data-sync-response.json | python3 -m json.tool

echo ""
echo "2. Waiting 10 seconds for data to sync..."
sleep 10

echo ""
echo "3. Verifying data in S3..."
aws s3 ls s3://$BUCKET/ --recursive | head -10

echo ""
echo "4. Triggering Analytics Lambda (creating new population file)..."
aws s3 cp \
  s3://$BUCKET/population_data_20260111_204633.json \
  s3://$BUCKET/population_data_e2e_test_$(date +%Y%m%d_%H%M%S).json

echo ""
echo "5. Waiting 10 seconds for Analytics Lambda to process..."
sleep 10

echo ""
echo "6. Checking Analytics Lambda logs..."
aws logs tail /aws/lambda/$ANALYTICS_LAMBDA --since 2m | grep -E "Query|Result|Processing" | tail -10

echo ""
echo "7. Checking SQS queue status..."
aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages' \
  --output text

echo ""
echo "=== Test Complete ==="
```

Save this as `test_e2e.sh`, make it executable, and run:

```bash
chmod +x test_e2e.sh
./test_e2e.sh
```

---

## Test 5: Verify All Components

### Checklist

- [ ] **Data Sync Lambda**
  - [ ] Executes successfully
  - [ ] Syncs BLS data to S3
  - [ ] Fetches and saves population data
  - [ ] Logs show success

- [ ] **S3 Bucket**
  - [ ] Contains BLS data file
  - [ ] Contains population JSON file
  - [ ] Files are accessible (public read)

- [ ] **SQS Queue**
  - [ ] Receives messages when JSON file created
  - [ ] Messages are processed

- [ ] **Analytics Lambda**
  - [ ] Triggers when population file created
  - [ ] Processes all 3 queries
  - [ ] Logs query results

- [ ] **EventBridge Schedule**
  - [ ] Rule is enabled
  - [ ] Targets Data Sync Lambda
  - [ ] Schedule is correct (daily at 2 AM UTC)

---

## Test 6: Verify Query Results

### Check Analytics Results in Logs

```bash
ANALYTICS_LAMBDA=$(terraform output -raw analytics_lambda_function_name)

# Get query results from logs
aws logs tail /aws/lambda/$ANALYTICS_LAMBDA --since 1h | \
  grep -A 5 "Query.*Results"
```

**Expected Output:**
```
Query 1 Results: {'mean': 322069808.0, 'std_dev': 4158441.040908095}
Query 2 Results: 282 records
Query 3 Results: 31 records
```

---

## Test 7: Test Data Cleaning

### Verify BLS Data Format

```bash
BUCKET=$(terraform output -raw s3_bucket_name)

# Download and check BLS data
aws s3 cp s3://$BUCKET/pr.data.0.Current /tmp/bls_data.txt

# Check first few lines
head -5 /tmp/bls_data.txt

# Check for whitespace issues (should be cleaned)
cat /tmp/bls_data.txt | head -1 | od -c | head -1
```

---

## Troubleshooting

### Data Sync Lambda Fails

```bash
# Check logs for errors
aws logs tail /aws/lambda/$DATA_SYNC_LAMBDA --since 1h | grep ERROR

# Common issues:
# - BLS source unreachable (check User-Agent header)
# - S3 permissions (check IAM role)
# - Timeout (increase Lambda timeout)
```

### Analytics Lambda Not Triggering

```bash
# Check SQS queue
aws sqs get-queue-attributes --queue-url $QUEUE_URL --attribute-names All

# Check S3 notification configuration
aws s3api get-bucket-notification-configuration --bucket $BUCKET

# Check Lambda event source mapping
aws lambda list-event-source-mappings --function-name $ANALYTICS_LAMBDA
```

### No Query Results in Logs

```bash
# Check if Lambda processed the message
aws logs tail /aws/lambda/$ANALYTICS_LAMBDA --since 1h

# Verify data files exist
aws s3 ls s3://$BUCKET/

# Check for import errors (NumPy, pandas)
aws logs tail /aws/lambda/$ANALYTICS_LAMBDA --since 1h | grep -i "error\|import"
```

---

## Quick Test Commands

### One-Liner Full Test

```bash
cd infrastructure/terraform && \
BUCKET=$(terraform output -raw s3_bucket_name) && \
LAMBDA=$(terraform output -raw data_sync_lambda_function_name) && \
aws lambda invoke --function-name $LAMBDA --payload '{}' /tmp/out.json && \
sleep 10 && \
aws s3 ls s3://$BUCKET/ && \
aws s3 cp s3://$BUCKET/population_data_20260111_204633.json s3://$BUCKET/test_$(date +%Y%m%d_%H%M%S).json && \
sleep 5 && \
aws logs tail /aws/lambda/$(terraform output -raw analytics_lambda_function_name) --since 2m | tail -20
```

---

## Expected Timeline

1. **Data Sync Lambda**: ~1-2 seconds
2. **S3 Upload**: ~1 second
3. **S3 → SQS**: ~1-2 seconds
4. **SQS → Analytics Lambda**: ~1 second
5. **Analytics Processing**: ~2-5 seconds
6. **Total**: ~5-10 seconds end-to-end

---

## Success Criteria

✅ **All tests pass if:**
- Data Sync Lambda completes successfully
- BLS data appears in S3
- Population data appears in S3
- Analytics Lambda triggers automatically
- Query results appear in CloudWatch logs
- No errors in any Lambda logs

