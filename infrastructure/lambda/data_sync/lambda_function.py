"""Data Sync Lambda: BLS sync + population fetch."""

import logging
import os
from typing import Any, Dict

from rearc.data_sync import sync_bls_data, fetch_and_save_population_data

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DEFAULT_REGION = 'us-east-1'
DEFAULT_ARCHIVE_PREFIX = 'archive/'


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Run BLS sync and population fetch; return status and any errors."""
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    region = os.environ.get('AWS_REGION', DEFAULT_REGION)
    archive_bucket = os.environ.get('S3_ARCHIVE_BUCKET')
    archive_prefix = os.environ.get('S3_ARCHIVE_PREFIX', DEFAULT_ARCHIVE_PREFIX)
    
    if not bucket_name:
        logger.error("S3_BUCKET_NAME environment variable not set")
        return {
            'statusCode': 500,
            'body': {'error': 'S3_BUCKET_NAME not configured'}
        }
    
    results: Dict[str, Any] = {
        'bls_sync': False,
        'population_fetch': False
    }
    
    try:
        logger.info("Starting BLS data sync...")
        bls_success = sync_bls_data(bucket_name, region, archive_bucket, archive_prefix)
        results['bls_sync'] = bls_success
        if bls_success:
            logger.info("BLS data sync completed")
        else:
            logger.error("BLS data sync failed")
        
    except Exception as e:
        logger.error(f"Error in BLS data sync: {str(e)}", exc_info=True)
        results['bls_sync'] = False
        results['bls_sync_error'] = str(e)
    try:
        logger.info("Starting population data fetch...")
        pop_success = fetch_and_save_population_data(bucket_name, region)
        results['population_fetch'] = pop_success
        if pop_success:
            logger.info("Population data fetch completed")
        else:
            logger.error("Population data fetch failed")
        
    except Exception as e:
        logger.error(f"Error in population data fetch: {str(e)}", exc_info=True)
        results['population_fetch'] = False
        results['population_fetch_error'] = str(e)
    status_code = 200 if (results['bls_sync'] or results['population_fetch']) else 500
    
    return {
        'statusCode': status_code,
        'body': results
    }

