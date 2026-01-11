#!/bin/bash
# Complete end-to-end test script

set -e

cd infrastructure/terraform

echo "=== End-to-End Pipeline Test ==="
echo ""

# Get resource names
BUCKET=$(terraform output -raw s3_bucket_name)
DATA_SYNC_LAMBDA=$(terraform output -raw data_sync_lambda_function_name)
ANALYTICS_LAMBDA=$(terraform output -raw analytics_lambda_function_name)
QUEUE_URL=$(terraform output -raw sqs_queue_url)

echo "📦 Resources:"
echo "   Bucket: $BUCKET"
echo "   Data Sync Lambda: $DATA_SYNC_LAMBDA"
echo "   Analytics Lambda: $ANALYTICS_LAMBDA"
echo ""

echo "1️⃣  Triggering Data Sync Lambda..."
aws lambda invoke \
  --function-name $DATA_SYNC_LAMBDA \
  --payload '{}' \
  /tmp/data-sync-response.json > /dev/null

echo "   ✓ Lambda invoked"
cat /tmp/data-sync-response.json | python3 -m json.tool 2>/dev/null || cat /tmp/data-sync-response.json
echo ""

echo "2️⃣  Waiting 10 seconds for data to sync..."
sleep 10

echo ""
echo "3️⃣  Verifying data in S3..."
echo "   Files in bucket:"
aws s3 ls s3://$BUCKET/ --recursive | head -10
echo ""

echo "4️⃣  Triggering Analytics Lambda (creating new population file)..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
aws s3 cp \
  s3://$BUCKET/population_data_20260111_204633.json \
  s3://$BUCKET/population_data_e2e_test_$TIMESTAMP.json > /dev/null

echo "   ✓ File created: population_data_e2e_test_$TIMESTAMP.json"
echo ""

echo "5️⃣  Waiting 10 seconds for Analytics Lambda to process..."
sleep 10

echo ""
echo "6️⃣  Checking Analytics Lambda logs..."
echo "   Recent log entries:"
aws logs tail /aws/lambda/$ANALYTICS_LAMBDA --since 2m 2>&1 | grep -E "Query|Result|Processing|ERROR" | tail -15 || echo "   (No matching log entries found)"

echo ""
echo "7️⃣  Checking SQS queue status..."
MESSAGES=$(aws sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names ApproximateNumberOfMessages \
  --query 'Attributes.ApproximateNumberOfMessages' \
  --output text 2>/dev/null || echo "0")
echo "   Messages in queue: $MESSAGES"

echo ""
echo "=== Test Complete ==="
echo ""
echo "✅ Check the logs above for query results"
echo "✅ If you see 'Query 1 Results', 'Query 2 Results', etc., everything is working!"
