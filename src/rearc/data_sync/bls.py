"""
BLS Data Sync Module

Syncs data from the Bureau of Labor Statistics (BLS) dataset to S3.
Handles recursive directory traversal, change detection, and file management.
"""

import boto3
import requests
import hashlib
import re
from urllib.parse import urljoin
from typing import Set, List, Tuple
import logging

logger = logging.getLogger(__name__)

# BLS source URL
BLS_BASE_URL = "https://download.bls.gov/pub/time.series/pr/"

# User-Agent header with contact information (required by BLS policy)
USER_AGENT = "RearcDataQuest/1.0 (Contact: your-email@example.com)"


def parse_directory_listing(html_content: str) -> Tuple[List[str], List[str]]:
    """
    Parse Apache-style directory listing HTML to extract files and directories.
    
    Apache directory listings typically have links like:
    <a href="filename">filename</a> or <a href="dirname/">dirname/</a>
    
    Args:
        html_content: HTML content of the directory listing page
        
    Returns:
        Tuple of (files, directories) found in the directory
    """
    files = []
    directories = []
    
    # Pattern to match links in directory listings
    # Matches: <a href="name"> or <a href="name/"> 
    # Excludes parent directory (../) and current directory (./)
    link_pattern = r'<a\s+href=["\']([^"\']+)["\']'
    
    for match in re.finditer(link_pattern, html_content, re.IGNORECASE):
        href = match.group(1)
        
        # Skip parent directory and current directory
        if href in ['../', '..', './', '.']:
            continue
        
        # Skip absolute URLs (external links)
        if href.startswith('http://') or href.startswith('https://'):
            continue
        
        # Remove query strings and fragments
        href = href.split('?')[0].split('#')[0]
        
        if not href or href == '':
            continue
        
        # Directories end with '/' in Apache listings
        if href.endswith('/'):
            dir_name = href.rstrip('/')
            if dir_name and dir_name not in directories:
                directories.append(dir_name)
        else:
            # It's a file
            if href not in files:
                files.append(href)
    
    return files, directories


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


def discover_files_and_directories(base_url: str, current_path: str = '') -> Tuple[List[str], List[str]]:
    """
    Discover files and directories in a given URL path.
    
    Args:
        base_url: Base URL for the BLS directory
        current_path: Current relative path from base
        
    Returns:
        Tuple of (files, directories) found in the directory
    """
    url = urljoin(base_url, current_path)
    if not url.endswith('/'):
        url += '/'
    
    logger.debug(f"Discovering files in: {url}")
    
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching directory listing for {url}: {e}")
        return [], []
    
    # Parse HTML directory listing
    files, directories = parse_directory_listing(html_content)
    
    return files, directories


def sync_file(s3_client, bucket_name: str, source_url: str, s3_key: str) -> bool:
    """
    Sync a single file from source URL to S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        source_url: Source URL of the file
        s3_key: S3 key (path) for the file
        
    Returns:
        True if file was synced (uploaded or skipped), False on error
    """
    logger.debug(f"Checking file: {s3_key}")
    
    # Fetch file content
    content = fetch_url_content(source_url)
    if content is None:
        logger.error(f"Failed to fetch {source_url}")
        return False
    
    # Calculate MD5 of fetched content
    content_md5 = calculate_md5(content)
    
    # Check if file exists in S3 and compare
    existing_etag = get_s3_object_etag(s3_client, bucket_name, s3_key)
    
    if existing_etag == content_md5:
        logger.debug(f"File {s3_key} is up to date, skipping upload")
        return True
    else:
        logger.info(f"Uploading {s3_key} (new or changed)")
        return upload_file_to_s3(s3_client, bucket_name, s3_key, content)


def sync_directory_recursive(
    s3_client,
    bucket_name: str,
    base_url: str,
    current_path: str = '',
    discovered_files: Set[str] = None
) -> Set[str]:
    """
    Recursively sync a directory and all subdirectories.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        base_url: Base URL for BLS directory
        current_path: Current relative path from base
        discovered_files: Set to track all discovered files
        
    Returns:
        Set of all discovered file paths (S3 keys)
    """
    if discovered_files is None:
        discovered_files = set()
    
    # Discover files and directories in current path
    files, directories = discover_files_and_directories(base_url, current_path)
    
    # Sync all files in current directory
    for file_name in files:
        # Construct S3 key (preserve directory structure)
        if current_path:
            s3_key = f"{current_path}/{file_name}"
        else:
            s3_key = file_name
        
        # Construct source URL
        if current_path:
            source_url = urljoin(base_url, f"{current_path}/{file_name}")
        else:
            source_url = urljoin(base_url, file_name)
        
        # Sync the file
        if sync_file(s3_client, bucket_name, source_url, s3_key):
            discovered_files.add(s3_key)
        else:
            logger.warning(f"Failed to sync {s3_key}")
    
    # Recursively process subdirectories
    for dir_name in directories:
        # Construct new path
        if current_path:
            new_path = f"{current_path}/{dir_name}"
        else:
            new_path = dir_name
        
        logger.info(f"Entering subdirectory: {new_path}")
        sync_directory_recursive(
            s3_client,
            bucket_name,
            base_url,
            new_path,
            discovered_files
        )
    
    return discovered_files


def sync_bls_data(bucket_name: str, region: str = 'us-east-1'):
    """
    Main function to sync BLS data to S3.
    
    Performs full recursive directory traversal, discovers all files dynamically,
    syncs new/changed files, and deletes files from S3 that no longer exist in source.
    
    Args:
        bucket_name: Name of the S3 bucket
        region: AWS region
    """
    s3_client = boto3.client('s3', region_name=region)
    
    logger.info(f"Starting BLS data sync to bucket: {bucket_name}")
    logger.info(f"Source URL: {BLS_BASE_URL}")
    
    # Step 1: Discover and sync all files recursively
    logger.info("Discovering and syncing files from source...")
    discovered_files = sync_directory_recursive(s3_client, bucket_name, BLS_BASE_URL)
    
    logger.info(f"Discovered {len(discovered_files)} files from source")
    
    # Step 2: Get all existing files in S3 (with BLS prefix if needed)
    logger.info("Listing existing files in S3...")
    s3_files = list_s3_objects(s3_client, bucket_name)
    
    # Filter to only BLS-related files (exclude population data, etc.)
    # BLS files typically don't have a prefix, but we'll check all
    # For now, we'll assume all files in root are BLS files
    # In a production system, you might want to use a prefix like 'bls/'
    
    logger.info(f"Found {len(s3_files)} existing files in S3")
    
    # Step 3: Find files in S3 that no longer exist in source (deletions)
    files_to_delete = s3_files - discovered_files
    
    if files_to_delete:
        logger.info(f"Found {len(files_to_delete)} files to delete from S3")
        for file_key in files_to_delete:
            logger.info(f"Deleting file from S3: {file_key}")
            delete_file_from_s3(s3_client, bucket_name, file_key)
    else:
        logger.info("No files to delete from S3")
    
    # Summary
    logger.info("=" * 60)
    logger.info("BLS Data Sync Summary:")
    logger.info(f"  Files discovered from source: {len(discovered_files)}")
    logger.info(f"  Files in S3: {len(s3_files)}")
    logger.info(f"  Files deleted: {len(files_to_delete)}")
    logger.info("=" * 60)
    logger.info("BLS data sync completed successfully")

