"""
BLS Data Sync Module

Main synchronization logic for syncing BLS data from source to S3.
Handles iterative directory traversal, change detection, and file management.
"""

import logging
import os
from typing import Any, Set, Optional
from collections import deque
from urllib.parse import urljoin

import boto3

from .bls_parser import discover_files_and_directories, fetch_url_content
from .bls_s3_ops import (
    calculate_md5,
    get_s3_object_etag,
    upload_file_to_s3,
    archive_file_to_s3,
    list_s3_objects,
    validate_directory_exists,
    DEFAULT_ARCHIVE_PREFIX,
    POPULATION_FILE_PREFIX,
)

logger = logging.getLogger(__name__)

# BLS source URL
BLS_BASE_URL = "https://download.bls.gov/pub/time.series/pr/"


def sync_file(
    s3_client: Any,
    bucket_name: str,
    source_url: str,
    s3_key: str
) -> bool:
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
    s3_client: Any,
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
    discovered_files: Set[str] = set()
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
            if not validate_directory_exists(base_url, new_path):
                logger.warning(f"Skipping invalid directory: {new_path}")
                continue
            
            logger.info(f"Queuing subdirectory: {new_path}")
            directories_to_process.append(new_path)
    
    logger.info(f"Completed iterative sync. Processed {len(discovered_files)} files")
    return discovered_files


def sync_bls_data(
    bucket_name: str,
    region: str = 'us-east-1',
    archive_bucket: Optional[str] = None,
    archive_prefix: str = DEFAULT_ARCHIVE_PREFIX
) -> bool:
    """
    Main function to sync BLS data to S3.
    
    Performs full iterative directory traversal using a queue, discovers all files dynamically,
    syncs new/changed files, and archives files from S3 that no longer exist in source.
    
    Args:
        bucket_name: Name of the S3 bucket
        region: AWS region
        archive_bucket: Archive bucket name (if None, uses bucket_name with archive_prefix)
        archive_prefix: Prefix for archive location (default: 'archive/')
        
    Returns:
        True if sync completed successfully, False otherwise
    """
    s3_client = boto3.client('s3', region_name=region)
    base_url = os.environ.get('BLS_SOURCE_URL', BLS_BASE_URL)
    
    logger.info(f"Starting BLS data sync to bucket: {bucket_name}")
    logger.info(f"Source URL: {base_url}")
    if archive_bucket:
        logger.info(f"Archive bucket: {archive_bucket}")
    else:
        logger.info(f"Archive prefix: {archive_prefix}")
    
    try:
        # Step 1: Discover and sync all files iteratively
        logger.info("Discovering and syncing files from source...")
        discovered_files = sync_directory_iterative(s3_client, bucket_name, base_url)
        
        logger.info(f"Discovered {len(discovered_files)} files from source")
        
        # Step 2: Get all existing files in S3
        logger.info("Listing existing files in S3...")
        s3_files = list_s3_objects(s3_client, bucket_name)
        
        # Filter to only BLS-related files:
        # - Exclude population data files (start with "population_data_")
        # - Exclude archive files (start with archive_prefix)
        # - Only process files that could be BLS files
        #
        # When archive_prefix is empty, do NOT use startswith('') in the filter:
        # str.startswith('') is True for all strings, so "not f.startswith('')"
        # would be False for every file, making bls_files_in_s3 empty and breaking
        # archiving. Only apply the archive-prefix exclusion when it is non-empty.
        archive_prefix_clean = archive_prefix.rstrip('/')
        bls_files_in_s3 = {
            f for f in s3_files
            if not f.startswith(POPULATION_FILE_PREFIX)
            and (not archive_prefix_clean or not f.startswith(archive_prefix_clean))
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
        
        return True
    except Exception as e:
        logger.error(f"Error during BLS data sync: {e}", exc_info=True)
        return False
