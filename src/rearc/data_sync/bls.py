"""
BLS Data Sync Module

Syncs data from the Bureau of Labor Statistics (BLS) dataset to S3.
Handles recursive directory traversal, change detection, and file management.
"""

import boto3
import requests
import hashlib
from urllib.parse import urljoin
from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)

# BLS source URL
BLS_BASE_URL = "https://download.bls.gov/pub/time.series/pr/"

# User-Agent header with contact information (required by BLS policy)
USER_AGENT = "RearcDataQuest/1.0 (Contact: your-email@example.com)"


def calculate_md5(content: bytes) -> str:
    """Calculate MD5 hash of content."""
    return hashlib.md5(content).hexdigest()


def get_s3_object_etag(s3_client, bucket: str, key: str) -> str:
    """Get ETag (MD5) of S3 object if it exists."""
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return response.get('ETag', '').strip('"')
    except s3_client.exceptions.NoSuchKey:
        return None
    except Exception as e:
        logger.error(f"Error checking S3 object {key}: {e}")
        return None


def upload_file_to_s3(s3_client, bucket: str, key: str, content: bytes) -> bool:
    """Upload file to S3."""
    try:
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType='text/plain' if key.endswith('.txt') else 'application/octet-stream'
        )
        logger.info(f"Uploaded: {key}")
        return True
    except Exception as e:
        logger.error(f"Error uploading {key}: {e}")
        return False


def delete_file_from_s3(s3_client, bucket: str, key: str) -> bool:
    """Delete file from S3."""
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted: {key}")
        return True
    except Exception as e:
        logger.error(f"Error deleting {key}: {e}")
        return False


def fetch_url_content(url: str) -> bytes:
    """Fetch content from URL with proper User-Agent header."""
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def list_s3_objects(s3_client, bucket: str, prefix: str = '') -> Set[str]:
    """List all objects in S3 bucket with given prefix."""
    objects = set()
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects.add(obj['Key'])
    except Exception as e:
        logger.error(f"Error listing S3 objects: {e}")
    return objects


def sync_bls_data(bucket_name: str, region: str = 'us-east-1'):
    """
    Main function to sync BLS data to S3.
    
    Args:
        bucket_name: Name of the S3 bucket
        region: AWS region
    """
    s3_client = boto3.client('s3', region_name=region)
    
    logger.info(f"Starting BLS data sync to bucket: {bucket_name}")
    
    # TODO: Implement file discovery logic
    # For now, we'll need to manually specify key files or implement
    # a more robust directory traversal
    
    # Example: Sync the main data file
    key_file = "pr.data.0.Current"
    url = urljoin(BLS_BASE_URL, key_file)
    
    logger.info(f"Fetching: {url}")
    content = fetch_url_content(url)
    
    if content is None:
        logger.error("Failed to fetch BLS data")
        return
    
    # Calculate MD5 of fetched content
    content_md5 = calculate_md5(content)
    
    # Check if file exists in S3 and compare
    existing_etag = get_s3_object_etag(s3_client, bucket_name, key_file)
    
    if existing_etag == content_md5:
        logger.info(f"File {key_file} is up to date, skipping upload")
    else:
        logger.info(f"Uploading {key_file} (new or changed)")
        upload_file_to_s3(s3_client, bucket_name, key_file, content)
    
    # TODO: Implement full directory traversal and sync logic
    # TODO: Handle file deletions (compare S3 objects with source)
    
    logger.info("BLS data sync completed")

