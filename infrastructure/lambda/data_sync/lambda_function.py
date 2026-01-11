"""
Lambda function for Data Sync (BLS + Population)

Combines BLS data sync and Population API fetch operations.
"""

import os
import logging
import boto3

# Import from the rearc package
from rearc.data_sync import sync_bls_data, fetch_and_save_population_data

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda handler for data sync operations.
    
    Args:
        event: EventBridge event (for scheduled trigger)
        context: Lambda context
        
    Returns:
        dict: Status of operations
    """
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    region = os.environ.get('AWS_REGION', 'us-east-1')
    
    if not bucket_name:
        logger.error("S3_BUCKET_NAME environment variable not set")
        return {
            'statusCode': 500,
            'body': 'S3_BUCKET_NAME not configured'
        }
    
    results = {
        'bls_sync': False,
        'population_fetch': False
    }
    
    try:
        # Sync BLS data
        logger.info("Starting BLS data sync...")
        sync_bls_data(bucket_name, region)
        results['bls_sync'] = True
        logger.info("BLS data sync completed")
        
    except Exception as e:
        logger.error(f"Error in BLS data sync: {str(e)}", exc_info=True)
        results['bls_sync_error'] = str(e)
    
    try:
        # Fetch population data
        logger.info("Starting population data fetch...")
        fetch_and_save_population_data(bucket_name, region)
        results['population_fetch'] = True
        logger.info("Population data fetch completed")
        
    except Exception as e:
        logger.error(f"Error in population data fetch: {str(e)}", exc_info=True)
        results['population_fetch_error'] = str(e)
    
    # Return success if at least one operation succeeded
    status_code = 200 if (results['bls_sync'] or results['population_fetch']) else 500
    
    return {
        'statusCode': status_code,
        'body': results
    }

