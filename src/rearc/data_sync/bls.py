"""
BLS Data Sync Module

Syncs data from the Bureau of Labor Statistics (BLS) dataset to S3.
Handles iterative directory traversal, change detection, and file management.
"""

import boto3
import requests
import hashlib
import re
from urllib.parse import urljoin
from typing import Set, List, Tuple
from collections import deque
from datetime import datetime
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
        
        # Extract just the filename/dirname from the href
        # Handle both relative paths (pr.class) and absolute paths (/pub/time.series/pr/pr.class)
        if '/' in href:
            # Extract the last component (filename or directory)
            href = href.rstrip('/').split('/')[-1]
        
        # Skip empty after processing
        if not href:
            continue
        
        # Directories end with '/' in Apache listings (but we already stripped it)
        # Check if original href ended with '/' to determine if it's a directory
        original_href = match.group(1).split('?')[0].split('#')[0]
        if original_href.endswith('/'):
            dir_name = href
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


def archive_file_to_s3(s3_client, source_bucket: str, source_key: str, 
                       archive_bucket: str = None, archive_prefix: str = 'archive/') -> bool:
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
    except Exception as e:
        logger.error(f"Error archiving {source_key}: {e}")
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
        # Log as warning for 404s (directory doesn't exist) vs error for other issues
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            logger.warning(f"Directory not found (404): {url} - skipping")
        else:
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


def sync_directory_iterative(
    s3_client,
    bucket_name: str,
    base_url: str
) -> Set[str]:
    """
    Iteratively sync a directory and all subdirectories using a queue.
    
    Uses a breadth-first traversal approach with a queue to avoid recursion
    and potential stack overflow issues with deep directory structures.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        base_url: Base URL for BLS directory
        
    Returns:
        Set of all discovered file paths (S3 keys)
    """
    discovered_files = set()
    directories_to_process = deque([''])  # Start with root directory (empty path)
    
    logger.info("Starting iterative directory sync")
    
    while directories_to_process:
        current_path = directories_to_process.popleft()
        
        logger.debug(f"Processing directory: {current_path if current_path else 'root'}")
        
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
        
        # Add subdirectories to queue for processing
        for dir_name in directories:
            # Construct new path
            if current_path:
                new_path = f"{current_path}/{dir_name}"
            else:
                new_path = dir_name
            
            # Validate directory exists before queuing (prevents 404 errors)
            # Quick HEAD request to check if directory is accessible
            test_url = urljoin(base_url, new_path)
            if not test_url.endswith('/'):
                test_url += '/'
            
            try:
                # Use HEAD request to check existence without downloading
                validation_response = requests.head(test_url, headers={'User-Agent': USER_AGENT}, timeout=5, allow_redirects=True)
                if validation_response.status_code != 200:
                    logger.warning(f"Skipping invalid directory (status {validation_response.status_code}): {new_path}")
                    continue
            except requests.exceptions.RequestException:
                # If validation fails, still queue it (let discover_files_and_directories handle the error)
                # This handles cases where HEAD might not work but GET does
                pass
            
            logger.info(f"Queuing subdirectory: {new_path}")
            directories_to_process.append(new_path)
    
    logger.info(f"Completed iterative sync. Processed {len(discovered_files)} files")
    return discovered_files


def sync_bls_data(bucket_name: str, region: str = 'us-east-1', 
                  archive_bucket: str = None, archive_prefix: str = 'archive/'):
    """
    Main function to sync BLS data to S3.
    
    Performs full iterative directory traversal using a queue, discovers all files dynamically,
    syncs new/changed files, and archives files from S3 that no longer exist in source.
    
    Args:
        bucket_name: Name of the S3 bucket
        region: AWS region
        archive_bucket: Archive bucket name (if None, uses bucket_name with archive_prefix)
        archive_prefix: Prefix for archive location (default: 'archive/')
    """
    s3_client = boto3.client('s3', region_name=region)
    
    logger.info(f"Starting BLS data sync to bucket: {bucket_name}")
    logger.info(f"Source URL: {BLS_BASE_URL}")
    if archive_bucket:
        logger.info(f"Archive bucket: {archive_bucket}")
    else:
        logger.info(f"Archive prefix: {archive_prefix}")
    
    # Step 1: Discover and sync all files iteratively
    logger.info("Discovering and syncing files from source...")
    discovered_files = sync_directory_iterative(s3_client, bucket_name, BLS_BASE_URL)
    
    logger.info(f"Discovered {len(discovered_files)} files from source")
    
    # Step 2: Get all existing files in S3
    logger.info("Listing existing files in S3...")
    s3_files = list_s3_objects(s3_client, bucket_name)
    
    # Filter to only BLS-related files:
    # - Exclude population data files (start with "population_data_")
    # - Exclude archive files (start with archive_prefix)
    # - Only process files that could be BLS files
    population_file_pattern = "population_data_"
    archive_prefix_clean = archive_prefix.rstrip('/')
    
    bls_files_in_s3 = {
        f for f in s3_files 
        if not f.startswith(population_file_pattern) 
        and not f.startswith(archive_prefix_clean)
    }
    
    logger.info(f"Found {len(s3_files)} total files in S3")
    logger.info(f"Found {len(bls_files_in_s3)} BLS-related files in S3 (excluding population and archive files)")
    
    # Step 3: Find BLS files in S3 that no longer exist in source (to archive)
    files_to_archive = bls_files_in_s3 - discovered_files
    
    if files_to_archive:
        logger.info(f"Found {len(files_to_archive)} BLS files to archive (removed from source)")
        for file_key in files_to_archive:
            logger.info(f"Archiving file: {file_key}")
            archive_file_to_s3(s3_client, bucket_name, file_key, archive_bucket, archive_prefix)
    else:
        logger.info("No BLS files to archive")
    
    # Summary
    logger.info("=" * 60)
    logger.info("BLS Data Sync Summary:")
    logger.info(f"  Files discovered from source: {len(discovered_files)}")
    logger.info(f"  Total files in S3: {len(s3_files)}")
    logger.info(f"  BLS files in S3: {len(bls_files_in_s3)}")
    logger.info(f"  Files archived: {len(files_to_archive)}")
    logger.info("=" * 60)
    logger.info("BLS data sync completed successfully")

