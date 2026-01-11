"""
Lambda function for Analytics

Processes SQS messages triggered by S3 events and runs analytics queries.
"""

import os
import json
import boto3
import pandas as pd
import logging
from io import StringIO

# Import from the rearc package
from rearc.analytics import (
    query1_population_stats,
    query2_best_year_per_series,
    query3_combined_report
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')


def load_data_from_s3(bucket_name: str, key: str) -> str:
    """Load data from S3 and return as string."""
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read().decode('utf-8')
    except Exception as e:
        logger.error(f"Error loading {key} from S3: {e}")
        raise


def lambda_handler(event, context):
    """
    Lambda handler for analytics processing.
    Triggered by SQS messages from S3 events.
    
    Args:
        event: SQS event containing S3 notification
        context: Lambda context
        
    Returns:
        dict: Results of analytics queries
    """
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    
    if not bucket_name:
        logger.error("S3_BUCKET_NAME environment variable not set")
        return {'statusCode': 500, 'body': 'S3_BUCKET_NAME not configured'}
    
    results = {}
    
    # Process each SQS record
    for record in event.get('Records', []):
        try:
            # Parse SQS message body (contains S3 event)
            body = json.loads(record['body'])
            s3_event = json.loads(body.get('Message', '{}'))
            
            # Extract S3 object information
            for s3_record in s3_event.get('Records', []):
                s3_object = s3_record['s3']
                object_key = s3_object['object']['key']
                object_bucket = s3_object['bucket']['name']
                
                logger.info(f"Processing S3 object: s3://{object_bucket}/{object_key}")
                
                # Only process if it's the population data JSON file
                if object_key.startswith('population_data_') and object_key.endswith('.json'):
                    # Load population data
                    population_content = load_data_from_s3(object_bucket, object_key)
                    population_data = json.loads(population_content)
                    population_df = pd.DataFrame(population_data.get('data', []))
                    
                    # Load BLS data
                    bls_key = 'pr.data.0.Current'
                    bls_content = load_data_from_s3(object_bucket, bls_key)
                    bls_df = pd.read_csv(StringIO(bls_content), sep='\t')
                    
                    # Clean data
                    string_columns = bls_df.select_dtypes(include=['object']).columns
                    for col in string_columns:
                        bls_df[col] = bls_df[col].str.strip()
                    
                    # Run queries
                    results['query1'] = query1_population_stats(population_df)
                    results['query2'] = query2_best_year_per_series(bls_df).to_dict('records')
                    results['query3'] = query3_combined_report(bls_df, population_df).to_dict('records')
                    
                    # Log results
                    logger.info(f"Query 1 Results: {results['query1']}")
                    logger.info(f"Query 2 Results: {len(results['query2'])} records")
                    logger.info(f"Query 3 Results: {len(results['query3'])} records")
                    
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}", exc_info=True)
            results['error'] = str(e)
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

