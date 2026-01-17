"""
Comprehensive test suite for BLS data sync functionality.
Tests directory traversal, file discovery, sync logic, and deletion handling.
"""
import sys
from pathlib import Path
from io import BytesIO
from unittest.mock import Mock, patch

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.data_sync.bls_parser import (
    parse_directory_listing,
    discover_files_and_directories,
    fetch_url_content,
)
from rearc.data_sync.bls_s3_ops import (
    calculate_md5,
    get_s3_object_etag,
    upload_file_to_s3,
    delete_file_from_s3,
    list_s3_objects,
)
from rearc.data_sync.bls_sync import (
    sync_file,
    sync_directory_iterative,
    sync_bls_data,
    BLS_BASE_URL,
)


class TestDirectoryListingParsing:
    """Test HTML directory listing parsing."""
    
    def test_parse_simple_directory(self) -> None:
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
    
    def test_parse_skip_parent_directory(self) -> None:
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
    
    def test_parse_apache_style_listing(self) -> None:
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
    
    @patch('rearc.data_sync.bls_parser.requests.get')
    def test_discover_files_and_directories(self, mock_get: Mock) -> None:
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
    
    @patch('rearc.data_sync.bls_parser.requests.get')
    def test_discover_handles_errors(self, mock_get: Mock) -> None:
        """Test that discovery handles HTTP errors gracefully."""
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        files, directories = discover_files_and_directories('https://example.com/', '')
        
        assert files == []
        assert directories == []


class TestS3Operations:
    """Test S3 operations with mocked boto3."""
    
    def test_calculate_md5(self) -> None:
        """Test MD5 calculation."""
        content = b"test content"
        md5 = calculate_md5(content)
        
        assert len(md5) == 32  # MD5 hex string length
        # Verify it's a valid MD5 hash (just check format, not exact value)
        assert all(c in '0123456789abcdef' for c in md5)
    
    def test_get_s3_object_etag_exists(self) -> None:
        """Test getting ETag for existing S3 object."""
        s3_client = Mock()
        s3_client.head_object.return_value = {'ETag': '"abc123"'}
        s3_client.exceptions.NoSuchKey = Exception
        
        etag = get_s3_object_etag(s3_client, 'bucket', 'key')
        
        assert etag == 'abc123'
        s3_client.head_object.assert_called_once_with(Bucket='bucket', Key='key')
    
    def test_get_s3_object_etag_not_exists(self) -> None:
        """Test getting ETag for non-existent S3 object."""
        from botocore.exceptions import ClientError
        s3_client = Mock()
        s3_client.exceptions.NoSuchKey = type('NoSuchKey', (Exception,), {})
        error_response = {'Error': {'Code': '404'}}
        s3_client.head_object.side_effect = ClientError(error_response, 'head_object')
        
        etag = get_s3_object_etag(s3_client, 'bucket', 'key')
        
        assert etag is None
    
    def test_upload_file_to_s3(self) -> None:
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
    
    def test_delete_file_from_s3(self) -> None:
        """Test deleting file from S3."""
        s3_client = Mock()
        s3_client.delete_object.return_value = {}
        
        result = delete_file_from_s3(s3_client, 'bucket', 'key')
        
        assert result is True
        s3_client.delete_object.assert_called_once_with(Bucket='bucket', Key='key')
    
    def test_list_s3_objects(self) -> None:
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
    
    @patch('rearc.data_sync.bls_sync.fetch_url_content')
    @patch('rearc.data_sync.bls_sync.get_s3_object_etag')
    @patch('rearc.data_sync.bls_sync.upload_file_to_s3')
    def test_sync_file_new(
        self,
        mock_upload: Mock,
        mock_get_etag: Mock,
        mock_fetch: Mock
    ) -> None:
        """Test syncing a new file (not in S3)."""
        s3_client = Mock()
        mock_fetch.return_value = b'file content'
        mock_get_etag.return_value = None  # File doesn't exist
        mock_upload.return_value = True
        
        result = sync_file(s3_client, 'bucket', 'https://example.com/file.txt', 'file.txt')
        
        assert result is True
        mock_upload.assert_called_once()
    
    @patch('rearc.data_sync.bls_sync.fetch_url_content')
    @patch('rearc.data_sync.bls_sync.get_s3_object_etag')
    @patch('rearc.data_sync.bls_sync.upload_file_to_s3')
    def test_sync_file_unchanged(
        self,
        mock_upload: Mock,
        mock_get_etag: Mock,
        mock_fetch: Mock
    ) -> None:
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
    
    @patch('rearc.data_sync.bls_sync.fetch_url_content')
    @patch('rearc.data_sync.bls_sync.get_s3_object_etag')
    @patch('rearc.data_sync.bls_sync.upload_file_to_s3')
    def test_sync_file_changed(
        self,
        mock_upload: Mock,
        mock_get_etag: Mock,
        mock_fetch: Mock
    ) -> None:
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
    
    @patch('rearc.data_sync.bls_sync.validate_directory_exists')
    @patch('rearc.data_sync.bls_sync.discover_files_and_directories')
    @patch('rearc.data_sync.bls_sync.sync_file')
    def test_sync_directory_iterative(
        self,
        mock_sync_file: Mock,
        mock_discover: Mock,
        mock_validate: Mock
    ) -> None:
        """Test iterative directory sync."""
        s3_client = Mock()
        
        # Mock discovery: root has files and a subdirectory
        def discover_side_effect(base_url: str, path: str) -> tuple:
            if path == '':
                return (['file1.txt', 'file2.txt'], ['subdir'])
            elif path == 'subdir':
                return (['subfile.txt'], [])
            return ([], [])
        
        mock_discover.side_effect = discover_side_effect
        mock_sync_file.return_value = True
        mock_validate.return_value = True  # All directories are valid
        
        discovered = sync_directory_iterative(s3_client, 'bucket', 'https://example.com/')
        
        # Should discover all files
        assert 'file1.txt' in discovered
        assert 'file2.txt' in discovered
        assert 'subdir/subfile.txt' in discovered
        
        # Should sync all files
        assert mock_sync_file.call_count == 3


class TestFullSync:
    """Test full BLS sync with mocked S3."""
    
    @patch('rearc.data_sync.bls_sync.sync_directory_iterative')
    @patch('rearc.data_sync.bls_sync.list_s3_objects')
    @patch('rearc.data_sync.bls_sync.archive_file_to_s3')
    @patch('rearc.data_sync.bls_sync.boto3.client')
    def test_sync_bls_data_full(
        self,
        mock_boto3_client: Mock,
        mock_archive: Mock,
        mock_list: Mock,
        mock_sync_iterative: Mock
    ) -> None:
        """Test full BLS sync including deletion handling."""
        s3_client = Mock()
        mock_boto3_client.return_value = s3_client
        
        # Mock discovered files
        discovered_files = {'file1.txt', 'file2.txt', 'pr.data.0.Current'}
        mock_sync_iterative.return_value = discovered_files
        
        # Mock existing S3 files (includes a file that should be deleted)
        existing_files = {'file1.txt', 'file2.txt', 'old_file.txt', 'pr.data.0.Current'}
        mock_list.return_value = existing_files
        
        mock_archive.return_value = True
        
        sync_bls_data('test-bucket', 'us-east-1')
        
        # Should archive old_file.txt (exists in S3 but not in source)
        assert mock_archive.called
    
    @patch('rearc.data_sync.bls_sync.sync_directory_iterative')
    @patch('rearc.data_sync.bls_sync.list_s3_objects')
    @patch('rearc.data_sync.bls_sync.archive_file_to_s3')
    @patch('rearc.data_sync.bls_sync.boto3.client')
    def test_sync_bls_data_no_deletions(
        self,
        mock_boto3_client: Mock,
        mock_archive: Mock,
        mock_list: Mock,
        mock_sync_iterative: Mock
    ) -> None:
        """Test sync when no files need deletion."""
        s3_client = Mock()
        mock_boto3_client.return_value = s3_client
        
        discovered_files = {'file1.txt', 'file2.txt'}
        mock_sync_iterative.return_value = discovered_files
        
        existing_files = {'file1.txt', 'file2.txt'}
        mock_list.return_value = existing_files
        
        sync_bls_data('test-bucket', 'us-east-1')
        
        # Should not archive anything
        mock_archive.assert_not_called()
