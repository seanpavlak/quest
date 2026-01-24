"""
BLS S3 Operations Module

Handles all S3 operations for BLS data sync including upload, download, delete, and archive.
"""

import hashlib
import logging
from typing import Any, Set, Optional
from datetime import datetime
from urllib.parse import urljoin

import boto3
import requests
from botocore.exceptions import ClientError, BotoCoreError

from .bls_parser import USER_AGENT

logger = logging.getLogger(__name__)

# Default archive prefix
DEFAULT_ARCHIVE_PREFIX = 'archive/'

# Population file prefix pattern
POPULATION_FILE_PREFIX = "population_data_"

# Request timeout for directory validation
VALIDATION_TIMEOUT = 5


def calculate_md5(content: bytes) -> str:
    """
    Calculate MD5 hash of content.
    
    Args:
        content: Content bytes to hash
        
    Returns:
        MD5 hash as hexadecimal string
    """
    return hashlib.md5(content).hexdigest()


def get_s3_object_etag(s3_client: Any, bucket: str, key: str) -> Optional[str]:
    """
    Get ETag (MD5) of S3 object if it exists.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        ETag string if object exists, None otherwise
    """
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return response.get('ETag', '').strip('"')
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == '404' or error_code == 'NoSuchKey':
            return None
        logger.error(f"Error checking S3 object {key}: {e}")
        return None
    except BotoCoreError as e:
        logger.error(f"BotoCore error checking S3 object {key}: {e}")
        return None


def upload_file_to_s3(
    s3_client: Any,
    bucket: str,
    key: str,
    content: bytes
) -> bool:
    """
    Upload file to S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        content: File content as bytes
        
    Returns:
        True if successful, False otherwise
    """
    try:
        content_type = 'text/plain' if key.endswith('.txt') else 'application/octet-stream'
        s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type
        )
        logger.info(f"Uploaded: {key}")
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error uploading {key}: {e}")
        return False


def archive_file_to_s3(
    s3_client: Any,
    source_bucket: str,
    source_key: str,
    archive_bucket: Optional[str] = None,
    archive_prefix: str = DEFAULT_ARCHIVE_PREFIX
) -> bool:
    """
    Archive a file by copying it to an archive location with a timestamp and then deleting the original.
    
    This ensures that if the same file is archived multiple times (e.g., removed from source,
    re-added, then removed again), each archive is preserved as a separate object.
    
    Args:
        s3_client: Boto3 S3 client
        source_bucket: Source bucket name
        source_key: Source object key
        archive_bucket: Archive bucket name (if None, uses source_bucket with prefix)
        archive_prefix: Prefix for archive location (default: 'archive/')
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Generate timestamp for unique archive key
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Extract filename and path components
        # If source_key has path separators, preserve the directory structure
        if '/' in source_key:
            path_parts = source_key.rsplit('/', 1)
            directory = path_parts[0] + '/'
            filename = path_parts[1]
        else:
            directory = ''
            filename = source_key
        
        # Create archive key with timestamp: archive/directory/filename_YYYYMMDD_HHMMSS
        # This preserves directory structure and ensures uniqueness
        timestamped_filename = f"{filename}_{timestamp}"
        if directory:
            archive_path = f"{directory}{timestamped_filename}"
        else:
            archive_path = timestamped_filename
        
        # Determine archive location
        if archive_bucket is None:
            archive_bucket = source_bucket
            archive_key = f"{archive_prefix}{archive_path}"
        else:
            archive_key = f"{archive_prefix}{archive_path}" if archive_prefix else archive_path
        
        # Copy object to archive location
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=archive_bucket,
            Key=archive_key
        )
        logger.info(f"Archived {source_key} to {archive_key}")
        
        # Delete original file
        s3_client.delete_object(Bucket=source_bucket, Key=source_key)
        logger.info(f"Deleted original: {source_key}")
        
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error archiving {source_key}: {e}")
        return False


def delete_file_from_s3(s3_client: Any, bucket: str, key: str) -> bool:
    """
    Delete file from S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        key: S3 object key
        
    Returns:
        True if successful, False otherwise
    """
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted: {key}")
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error deleting {key}: {e}")
        return False


def list_s3_objects(s3_client: Any, bucket: str, prefix: str = '') -> Set[str]:
    """
    List all objects in S3 bucket with given prefix.
    
    Args:
        s3_client: Boto3 S3 client
        bucket: S3 bucket name
        prefix: Optional prefix to filter objects
        
    Returns:
        Set of object keys
    """
    objects: Set[str] = set()
    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    objects.add(obj['Key'])
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error listing S3 objects: {e}")
    return objects


def validate_directory_exists(base_url: str, path: str) -> bool:
    """
    Validate that a directory exists by making a HEAD request.
    
    Args:
        base_url: Base URL for the directory
        path: Directory path to validate
        
    Returns:
        True if directory exists and is accessible, False otherwise
    """
    test_url = urljoin(base_url, path)
    if not test_url.endswith('/'):
        test_url += '/'
    
    try:
        validation_response = requests.head(
            test_url,
            headers={'User-Agent': USER_AGENT},
            timeout=VALIDATION_TIMEOUT,
            allow_redirects=True
        )
        return validation_response.status_code == 200
    except requests.exceptions.RequestException:
        # If validation fails, return False
        # This handles cases where HEAD might not work but GET does
        return False
