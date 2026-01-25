"""Apache-style directory listing parsing and URL fetching."""

import re
import logging
from typing import List, Tuple, Optional
from urllib.parse import urljoin
import requests

logger = logging.getLogger(__name__)

USER_AGENT = "RearcDataQuest/1.0 (Contact: your-email@example.com)"
REQUEST_TIMEOUT = 30


def parse_directory_listing(html_content: str) -> Tuple[List[str], List[str]]:
    """Parse Apache-style HTML index: returns (file_names, directory_names)."""
    files: List[str] = []
    directories: List[str] = []
    link_pattern = r'<a\s+href=["\']([^"\']+)["\']'
    for match in re.finditer(link_pattern, html_content, re.IGNORECASE):
        href = match.group(1)
        if href in ['../', '..', './', '.']:
            continue
        if href.startswith('http://') or href.startswith('https://'):
            continue
        href = href.split('?')[0].split('#')[0]
        if not href or href == '':
            continue
        if '/' in href:
            href = href.rstrip('/').split('/')[-1]
        if not href:
            continue
        original_href = match.group(1).split('?')[0].split('#')[0]
        if original_href.endswith('/'):
            dir_name = href
            if dir_name and dir_name not in directories:
                directories.append(dir_name)
        else:
            if href not in files:
                files.append(href)
    return files, directories


def fetch_url_content(url: str) -> Optional[bytes]:
    """GET url; returns raw bytes or None on error."""
    headers = {'User-Agent': USER_AGENT}
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None


def discover_files_and_directories(base_url: str, current_path: str = '') -> Tuple[List[str], List[str]]:
    """Fetch dir listing at base_url/current_path and parse into files and subdirs."""
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
        if e.response is not None and e.response.status_code == 404:
            logger.warning(f"Directory not found (404): {url} - skipping")
        else:
            logger.error(f"HTTP error fetching directory listing for {url}: {e}")
        return [], []
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching directory listing for {url}: {e}")
        return [], []
    files, directories = parse_directory_listing(html_content)
    return files, directories
