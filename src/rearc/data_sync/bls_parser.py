"""
BLS Directory Parser Module

Handles parsing of Apache-style directory listings and URL content fetching.
"""

import re
import logging
from typing import List, Tuple, Optional
from urllib.parse import urljoin
import requests

logger = logging.getLogger(__name__)

# User-Agent header with contact information (required by BLS policy)
USER_AGENT = "RearcDataQuest/1.0 (Contact: your-email@example.com)"

# Request timeout in seconds
REQUEST_TIMEOUT = 30


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
    files: List[str] = []
    directories: List[str] = []
    
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


def fetch_url_content(url: str) -> Optional[bytes]:
    """
    Fetch content from URL with proper User-Agent header.
    
    Args:
        url: URL to fetch
        
    Returns:
        Content as bytes if successful, None otherwise
    """
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


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
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.HTTPError as e:
        # Log as warning for 404s (directory doesn't exist) vs error for other issues
        if e.response is not None and e.response.status_code == 404:
            logger.warning(f"Directory not found (404): {url} - skipping")
        else:
            logger.error(f"HTTP error fetching directory listing for {url}: {e}")
        return [], []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching directory listing for {url}: {e}")
        return [], []
    
    # Parse HTML directory listing
    files, directories = parse_directory_listing(html_content)
    
    return files, directories
