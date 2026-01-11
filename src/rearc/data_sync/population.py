"""
Population Data API Fetch Module

Fetches population data from the DataUSA API and saves it to S3.
"""

import boto3
import requests
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# DataUSA API URL
DATAUSA_API_URL = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"


def fetch_population_data(api_url: str) -> dict:
    """
    Fetch population data from DataUSA API.
    
    Args:
        api_url: URL of the DataUSA API endpoint
        
    Returns:
        JSON response as dictionary, or None if error
    """
    try:
        logger.info(f"Fetching data from: {api_url}")
        response = requests.get(api_url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched {len(data.get('data', []))} records")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from API: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response: {e}")
        return None


def save_to_s3(bucket_name: str, data: dict, key: str = None, region: str = 'us-east-1') -> bool:
    """
    Save JSON data to S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        data: Dictionary to save as JSON
        key: S3 object key (filename). If None, uses timestamp-based name
        region: AWS region
        
    Returns:
        True if successful, False otherwise
    """
    s3_client = boto3.client('s3', region_name=region)
    
    if key is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        key = f"population_data_{timestamp}.json"
    
    try:
        json_content = json.dumps(data, indent=2)
        s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=json_content.encode('utf-8'),
            ContentType='application/json'
        )
        logger.info(f"Saved data to s3://{bucket_name}/{key}")
        return True
    except Exception as e:
        logger.error(f"Error saving to S3: {e}")
        return False


def fetch_and_save_population_data(bucket_name: str, region: str = 'us-east-1', key: str = None):
    """
    Main function to fetch population data and save to S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        region: AWS region
        key: Optional S3 object key. If None, uses timestamp-based name
    """
    logger.info(f"Starting population data fetch and save to bucket: {bucket_name}")
    
    # Fetch data from API
    data = fetch_population_data(DATAUSA_API_URL)
    
    if data is None:
        logger.error("Failed to fetch population data")
        return False
    
    # Save to S3
    success = save_to_s3(bucket_name, data, key, region)
    
    if success:
        logger.info("Population data fetch and save completed successfully")
    else:
        logger.error("Failed to save population data to S3")
    
    return success

