"""
Unit tests for CLI module.
Tests command-line interface functionality.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from io import StringIO

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.cli import main


class TestCLI:
    """Test CLI commands."""
    
    @patch('rearc.cli.sync_bls_data')
    @patch('sys.argv', ['cli.py', 'sync-bls', 'test-bucket'])
    def test_sync_bls_command(self, mock_sync: Mock) -> None:
        """Test sync-bls command."""
        mock_sync.return_value = True
        
        try:
            main()
        except SystemExit:
            pass  # Expected - argparse calls sys.exit
        
        mock_sync.assert_called_once_with('test-bucket', 'us-east-1', archive_bucket=None, archive_prefix='archive/')
    
    @patch('rearc.cli.sync_bls_data')
    @patch('sys.argv', ['cli.py', 'sync-bls', 'test-bucket', '--region', 'us-west-2'])
    def test_sync_bls_command_with_region(self, mock_sync: Mock) -> None:
        """Test sync-bls command with custom region."""
        mock_sync.return_value = True
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_sync.assert_called_once_with('test-bucket', 'us-west-2', archive_bucket=None, archive_prefix='archive/')
    
    @patch('rearc.cli.fetch_and_save_population_data')
    @patch('sys.argv', ['cli.py', 'fetch-population', 'test-bucket'])
    def test_fetch_population_command(self, mock_fetch: Mock) -> None:
        """Test fetch-population command."""
        mock_fetch.return_value = True
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_fetch.assert_called_once_with('test-bucket', 'us-east-1', None)
    
    @patch('rearc.cli.fetch_and_save_population_data')
    @patch('sys.argv', ['cli.py', 'fetch-population', 'test-bucket', '--key', 'custom-key.json'])
    def test_fetch_population_command_with_key(self, mock_fetch: Mock) -> None:
        """Test fetch-population command with custom key."""
        mock_fetch.return_value = True
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_fetch.assert_called_once_with('test-bucket', 'us-east-1', 'custom-key.json')
    
    @patch('rearc.cli.fetch_and_save_population_data')
    @patch('rearc.cli.sync_bls_data')
    @patch('sys.argv', ['cli.py', 'sync-all', 'test-bucket'])
    def test_sync_all_command(
        self,
        mock_sync_bls: Mock,
        mock_fetch_pop: Mock
    ) -> None:
        """Test sync-all command."""
        mock_sync_bls.return_value = True
        mock_fetch_pop.return_value = True
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_sync_bls.assert_called_once_with('test-bucket', 'us-east-1', archive_bucket=None, archive_prefix='archive/')
        mock_fetch_pop.assert_called_once_with('test-bucket', 'us-east-1')
    
    @patch('sys.argv', ['cli.py'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_no_command_prints_help(self, mock_stdout: StringIO) -> None:
        """Test that no command prints help."""
        try:
            main()
        except SystemExit as e:
            assert e.code == 1  # argparse exits with code 1 for no command
    
    @patch('rearc.cli.sync_bls_data')
    @patch('sys.argv', ['cli.py', 'sync-bls', 'test-bucket'])
    def test_command_error_handling(self, mock_sync: Mock) -> None:
        """Test error handling in commands."""
        mock_sync.side_effect = Exception("Test error")
        
        try:
            main()
        except SystemExit as e:
            assert e.code == 1  # Should exit with error code
