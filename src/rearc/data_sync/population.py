"""Fetch population data from DataUSA API and save to S3."""

import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

import boto3
import requests
from botocore.exceptions import ClientError, BotoCoreError

logger = logging.getLogger(__name__)

DATAUSA_API_URL = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"
REQUEST_TIMEOUT = 30
DEFAULT_REGION = 'us-east-1'
POPULATION_FILE_PREFIX = "population_data_"


def fetch_population_data(api_url: str) -> Optional[Dict[str, Any]]:
    """GET JSON from DataUSA-style API; returns parsed data or None on error."""
    try:
        logger.info(f"Fetching data from: {api_url}")
        response = requests.get(api_url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Successfully fetched {len(data.get('data', []))} records")
        return data
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error fetching data from API: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from API: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON response: {e}")
        return None


def save_to_s3(
    bucket_name: str,
    data: Dict[str, Any],
    key: Optional[str] = None,
    region: str = DEFAULT_REGION
) -> bool:
    """Save JSON dict to S3; key defaults to population_data_<timestamp>.json."""
    if key is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        key = f"{POPULATION_FILE_PREFIX}{timestamp}.json"
    
    s3_client = boto3.client('s3', region_name=region)
    
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
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error saving to S3: {e}")
        return False


def fetch_and_save_population_data(
    bucket_name: str,
    region: str = DEFAULT_REGION,
    key: Optional[str] = None
) -> bool:
    """Fetch from DataUSA API and save to S3; skips save if API returns empty data."""
    logger.info(f"Starting population data fetch and save to bucket: {bucket_name}")
    api_url = os.environ.get('DATAUSA_API_URL', DATAUSA_API_URL)
    data = fetch_population_data(api_url)
    if data is None:
        logger.error("Failed to fetch population data")
        return False
    if not data.get('data', []):
        logger.warning("API returned empty data array; skipping save to avoid triggering analytics on empty file")
        return False
    success = save_to_s3(bucket_name, data, key, region)
    
    if success:
        logger.info("Population data fetch and save completed successfully")
    else:
        logger.error("Failed to save population data to S3")
    
    return success

