"""
Comprehensive test suite for BLS data sync functionality.
Tests directory traversal, file discovery, sync logic, and deletion handling.
"""
import sys
from pathlib import Path
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from io import BytesIO

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.data_sync.bls import (
    parse_directory_listing,
    discover_files_and_directories,
    sync_file,
    sync_directory_iterative,
    sync_bls_data,
    calculate_md5,
    get_s3_object_etag,
    upload_file_to_s3,
    delete_file_from_s3,
    list_s3_objects,
    fetch_url_content,
    BLS_BASE_URL
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestDirectoryListingParsing:
    """Test HTML directory listing parsing."""
    
    def test_parse_simple_directory(self):
        """Test parsing a simple directory listing."""
        html = """
        <html>
        <body>
        <table>
        <tr><td><a href="file1.txt">file1.txt</a></td></tr>
        <tr><td><a href="file2.csv">file2.csv</a></td></tr>
        <tr><td><a href="subdir/">subdir/</a></td></tr>
        </table>
        </body>
        </html>
        """
        
        files, directories = parse_directory_listing(html)
        
        assert 'file1.txt' in files
        assert 'file2.csv' in files
        assert 'subdir' in directories
        assert len(files) == 2
        assert len(directories) == 1
    
    def test_parse_skip_parent_directory(self):
        """Test that parent directory links are skipped."""
        html = """
        <html>
        <body>
        <table>
        <tr><td><a href="../">Parent Directory</a></td></tr>
        <tr><td><a href="file.txt">file.txt</a></td></tr>
        </table>
        </body>
        </html>
        """
        
        files, directories = parse_directory_listing(html)
        
        assert '../' not in files
        assert '../' not in directories
        assert 'file.txt' in files
    
    def test_parse_apache_style_listing(self):
        """Test parsing Apache-style directory listing."""
        html = """
        <html>
        <head><title>Index of /pub/time.series/pr/</title></head>
        <body>
        <h1>Index of /pub/time.series/pr/</h1>
        <table>
        <tr><th>Name</th><th>Last modified</th><th>Size</th></tr>
        <tr><td><a href="../">Parent Directory</a></td></tr>
        <tr><td><a href="pr.data.0.Current">pr.data.0.Current</a></td><td>2024-01-01</td><td>1.5M</td></tr>
        <tr><td><a href="pr.series">pr.series</a></td><td>2024-01-01</td><td>50K</td></tr>
        <tr><td><a href="data/">data/</a></td><td>2024-01-01</td><td>-</td></tr>
        </table>
        </body>
        </html>
        """
        
        files, directories = parse_directory_listing(html)
        
        assert 'pr.data.0.Current' in files
        assert 'pr.series' in files
        assert 'data' in directories
        assert '../' not in files
        assert '../' not in directories


class TestFileDiscovery:
    """Test file and directory discovery."""
    
    @patch('rearc.data_sync.bls.requests.get')
    def test_discover_files_and_directories(self, mock_get):
        """Test discovering files and directories from a URL."""
        # Mock HTML response
        mock_response = Mock()
        mock_response.text = """
        <html><body><table>
        <tr><td><a href="file1.txt">file1.txt</a></td></tr>
        <tr><td><a href="subdir/">subdir/</a></td></tr>
        </table></body></html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        files, directories = discover_files_and_directories('https://example.com/', '')
        
        assert 'file1.txt' in files
        assert 'subdir' in directories
        mock_get.assert_called_once()
    
    @patch('rearc.data_sync.bls.requests.get')
    def test_discover_handles_errors(self, mock_get):
        """Test that discovery handles HTTP errors gracefully."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        files, directories = discover_files_and_directories('https://example.com/', '')
        
        assert files == []
        assert directories == []


class TestS3Operations:
    """Test S3 operations with mocked boto3."""
    
    def test_calculate_md5(self):
        """Test MD5 calculation."""
        content = b"test content"
        md5 = calculate_md5(content)
        
        assert len(md5) == 32  # MD5 hex string length
        # Verify it's a valid MD5 hash (just check format, not exact value)
        assert all(c in '0123456789abcdef' for c in md5)
    
    def test_get_s3_object_etag_exists(self):
        """Test getting ETag for existing S3 object."""
        s3_client = Mock()
        s3_client.head_object.return_value = {'ETag': '"abc123"'}
        s3_client.exceptions.NoSuchKey = Exception
        
        etag = get_s3_object_etag(s3_client, 'bucket', 'key')
        
        assert etag == 'abc123'
        s3_client.head_object.assert_called_once_with(Bucket='bucket', Key='key')
    
    def test_get_s3_object_etag_not_exists(self):
        """Test getting ETag for non-existent S3 object."""
        s3_client = Mock()
        s3_client.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})
        s3_client.head_object.side_effect = s3_client.exceptions.NoSuchKey()
        
        etag = get_s3_object_etag(s3_client, 'bucket', 'key')
        
        assert etag is None
    
    def test_upload_file_to_s3(self):
        """Test uploading file to S3."""
        s3_client = Mock()
        s3_client.put_object.return_value = {}
        
        result = upload_file_to_s3(s3_client, 'bucket', 'key', b'content')
        
        assert result is True
        s3_client.put_object.assert_called_once()
        call_kwargs = s3_client.put_object.call_args[1]
        assert call_kwargs['Bucket'] == 'bucket'
        assert call_kwargs['Key'] == 'key'
        assert call_kwargs['Body'] == b'content'
    
    def test_delete_file_from_s3(self):
        """Test deleting file from S3."""
        s3_client = Mock()
        s3_client.delete_object.return_value = {}
        
        result = delete_file_from_s3(s3_client, 'bucket', 'key')
        
        assert result is True
        s3_client.delete_object.assert_called_once_with(Bucket='bucket', Key='key')
    
    def test_list_s3_objects(self):
        """Test listing S3 objects."""
        s3_client = Mock()
        paginator = Mock()
        s3_client.get_paginator.return_value = paginator
        
        # Mock paginated results
        page1 = {'Contents': [{'Key': 'file1.txt'}, {'Key': 'file2.txt'}]}
        page2 = {'Contents': [{'Key': 'file3.txt'}]}
        paginator.paginate.return_value = [page1, page2]
        
        objects = list_s3_objects(s3_client, 'bucket')
        
        assert 'file1.txt' in objects
        assert 'file2.txt' in objects
        assert 'file3.txt' in objects
        assert len(objects) == 3


class TestFileSync:
    """Test file synchronization logic."""
    
    @patch('rearc.data_sync.bls.fetch_url_content')
    @patch('rearc.data_sync.bls.get_s3_object_etag')
    @patch('rearc.data_sync.bls.upload_file_to_s3')
    def test_sync_file_new(self, mock_upload, mock_get_etag, mock_fetch):
        """Test syncing a new file (not in S3)."""
        s3_client = Mock()
        mock_fetch.return_value = b'file content'
        mock_get_etag.return_value = None  # File doesn't exist
        mock_upload.return_value = True
        
        result = sync_file(s3_client, 'bucket', 'https://example.com/file.txt', 'file.txt')
        
        assert result is True
        mock_upload.assert_called_once()
    
    @patch('rearc.data_sync.bls.fetch_url_content')
    @patch('rearc.data_sync.bls.get_s3_object_etag')
    @patch('rearc.data_sync.bls.upload_file_to_s3')
    def test_sync_file_unchanged(self, mock_upload, mock_get_etag, mock_fetch):
        """Test syncing an unchanged file (same MD5)."""
        s3_client = Mock()
        content = b'file content'
        md5 = calculate_md5(content)
        
        mock_fetch.return_value = content
        mock_get_etag.return_value = md5  # Same MD5
        mock_upload.return_value = True
        
        result = sync_file(s3_client, 'bucket', 'https://example.com/file.txt', 'file.txt')
        
        assert result is True
        mock_upload.assert_not_called()  # Should skip upload
    
    @patch('rearc.data_sync.bls.fetch_url_content')
    @patch('rearc.data_sync.bls.get_s3_object_etag')
    @patch('rearc.data_sync.bls.upload_file_to_s3')
    def test_sync_file_changed(self, mock_upload, mock_get_etag, mock_fetch):
        """Test syncing a changed file (different MD5)."""
        s3_client = Mock()
        content = b'new file content'
        old_md5 = 'old_md5_hash'
        
        mock_fetch.return_value = content
        mock_get_etag.return_value = old_md5  # Different MD5
        mock_upload.return_value = True
        
        result = sync_file(s3_client, 'bucket', 'https://example.com/file.txt', 'file.txt')
        
        assert result is True
        mock_upload.assert_called_once()  # Should upload


class TestRecursiveSync:
    """Test iterative directory synchronization."""
    
    @patch('rearc.data_sync.bls.requests.head')
    @patch('rearc.data_sync.bls.discover_files_and_directories')
    @patch('rearc.data_sync.bls.sync_file')
    def test_sync_directory_iterative(self, mock_sync_file, mock_discover, mock_head):
        """Test iterative directory sync."""
        s3_client = Mock()
        
        # Mock discovery: root has files and a subdirectory
        def discover_side_effect(base_url, path):
            if path == '':
                return (['file1.txt', 'file2.txt'], ['subdir'])
            elif path == 'subdir':
                return (['subfile.txt'], [])
            return ([], [])
        
        mock_discover.side_effect = discover_side_effect
        mock_sync_file.return_value = True
        
        # Mock HEAD request for directory validation (returns 200 for valid directories)
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head.return_value = mock_head_response
        
        discovered = sync_directory_iterative(s3_client, 'bucket', 'https://example.com/')
        
        # Should discover all files
        assert 'file1.txt' in discovered
        assert 'file2.txt' in discovered
        assert 'subdir/subfile.txt' in discovered
        
        # Should sync all files
        assert mock_sync_file.call_count == 3


class TestFullSync:
    """Test full BLS sync with mocked S3."""
    
    @patch('rearc.data_sync.bls.sync_directory_iterative')
    @patch('rearc.data_sync.bls.list_s3_objects')
    @patch('rearc.data_sync.bls.delete_file_from_s3')
    def test_sync_bls_data_full(self, mock_delete, mock_list, mock_sync_iterative):
        """Test full BLS sync including deletion handling."""
        s3_client = Mock()
        
        # Mock discovered files
        discovered_files = {'file1.txt', 'file2.txt', 'pr.data.0.Current'}
        mock_sync_iterative.return_value = discovered_files
        
        # Mock existing S3 files (includes a file that should be deleted)
        existing_files = {'file1.txt', 'file2.txt', 'old_file.txt', 'pr.data.0.Current'}
        mock_list.return_value = existing_files
        
        mock_delete.return_value = True
        
        # Mock boto3.client
        with patch('rearc.data_sync.bls.boto3.client', return_value=s3_client):
            sync_bls_data('test-bucket', 'us-east-1')
        
        # Should delete old_file.txt (exists in S3 but not in source)
        mock_delete.assert_called_once_with(s3_client, 'test-bucket', 'old_file.txt')
    
    @patch('rearc.data_sync.bls.sync_directory_iterative')
    @patch('rearc.data_sync.bls.list_s3_objects')
    @patch('rearc.data_sync.bls.delete_file_from_s3')
    def test_sync_bls_data_no_deletions(self, mock_delete, mock_list, mock_sync_iterative):
        """Test sync when no files need deletion."""
        s3_client = Mock()
        
        discovered_files = {'file1.txt', 'file2.txt'}
        mock_sync_iterative.return_value = discovered_files
        
        existing_files = {'file1.txt', 'file2.txt'}
        mock_list.return_value = existing_files
        
        with patch('rearc.data_sync.bls.boto3.client', return_value=s3_client):
            sync_bls_data('test-bucket', 'us-east-1')
        
        # Should not delete anything
        mock_delete.assert_not_called()


def run_all_tests():
    """Run all test classes."""
    logger.info("=" * 60)
    logger.info("Running BLS Sync Test Suite")
    logger.info("=" * 60)
    
    test_classes = [
        TestDirectoryListingParsing,
        TestFileDiscovery,
        TestS3Operations,
        TestFileSync,
        TestRecursiveSync,
        TestFullSync
    ]
    
    results = {}
    
    for test_class in test_classes:
        class_name = test_class.__name__
        logger.info(f"\n--- {class_name} ---")
        
        test_instance = test_class()
        methods = [m for m in dir(test_instance) if m.startswith('test_')]
        
        class_results = {}
        for method_name in methods:
            try:
                method = getattr(test_instance, method_name)
                method()
                class_results[method_name] = True
                logger.info(f"  ✓ {method_name}")
            except Exception as e:
                class_results[method_name] = False
                logger.error(f"  ✗ {method_name}: {e}")
        
        results[class_name] = class_results
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    
    total_tests = 0
    passed_tests = 0
    
    for class_name, class_results in results.items():
        for test_name, passed in class_results.items():
            total_tests += 1
            if passed:
                passed_tests += 1
            status = "✓ PASS" if passed else "✗ FAIL"
            logger.info(f"{class_name}.{test_name:30} {status}")
    
    logger.info("=" * 60)
    logger.info(f"Total: {total_tests}, Passed: {passed_tests}, Failed: {total_tests - passed_tests}")
    logger.info("=" * 60)
    
    return passed_tests == total_tests


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

