"""S3 ops for BLS sync: upload, delete, archive, list, validate."""

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

DEFAULT_ARCHIVE_PREFIX = 'archive/'
POPULATION_FILE_PREFIX = "population_data_"
VALIDATION_TIMEOUT = 5


def calculate_md5(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


def get_s3_object_etag(s3_client: Any, bucket: str, key: str) -> Optional[str]:
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
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        if '/' in source_key:
            path_parts = source_key.rsplit('/', 1)
            directory = path_parts[0] + '/'
            filename = path_parts[1]
        else:
            directory = ''
            filename = source_key
        timestamped_filename = f"{filename}_{timestamp}"
        if directory:
            archive_path = f"{directory}{timestamped_filename}"
        else:
            archive_path = timestamped_filename
        if archive_bucket is None:
            archive_bucket = source_bucket
            archive_key = f"{archive_prefix}{archive_path}"
        else:
            archive_key = f"{archive_prefix}{archive_path}" if archive_prefix else archive_path
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=archive_bucket,
            Key=archive_key
        )
        logger.info(f"Archived {source_key} to {archive_key}")
        s3_client.delete_object(Bucket=source_bucket, Key=source_key)
        logger.info(f"Deleted original: {source_key}")
        
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error archiving {source_key}: {e}")
        return False


def delete_file_from_s3(s3_client: Any, bucket: str, key: str) -> bool:
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted: {key}")
        return True
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error deleting {key}: {e}")
        return False


def list_s3_objects(s3_client: Any, bucket: str, prefix: str = '') -> Set[str]:
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
        return False
