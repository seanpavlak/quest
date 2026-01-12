"""
Unit tests for CLI module.
Tests command-line interface functionality.
"""
import sys
from pathlib import Path
import logging
from unittest.mock import patch, Mock
from io import StringIO

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.cli import main

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestCLI:
    """Test CLI commands."""
    
    @patch('rearc.cli.sync_bls_data')
    @patch('sys.argv', ['cli.py', 'sync-bls', 'test-bucket'])
    def test_sync_bls_command(self, mock_sync):
        """Test sync-bls command."""
        mock_sync.return_value = None
        
        try:
            main()
        except SystemExit:
            pass  # Expected - argparse calls sys.exit
        
        mock_sync.assert_called_once_with('test-bucket', 'us-east-1')
    
    @patch('rearc.cli.sync_bls_data')
    @patch('sys.argv', ['cli.py', 'sync-bls', 'test-bucket', '--region', 'us-west-2'])
    def test_sync_bls_command_with_region(self, mock_sync):
        """Test sync-bls command with custom region."""
        mock_sync.return_value = None
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_sync.assert_called_once_with('test-bucket', 'us-west-2')
    
    @patch('rearc.cli.fetch_and_save_population_data')
    @patch('sys.argv', ['cli.py', 'fetch-population', 'test-bucket'])
    def test_fetch_population_command(self, mock_fetch):
        """Test fetch-population command."""
        mock_fetch.return_value = True
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_fetch.assert_called_once_with('test-bucket', 'us-east-1', None)
    
    @patch('rearc.cli.fetch_and_save_population_data')
    @patch('sys.argv', ['cli.py', 'fetch-population', 'test-bucket', '--key', 'custom-key.json'])
    def test_fetch_population_command_with_key(self, mock_fetch):
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
    def test_sync_all_command(self, mock_sync_bls, mock_fetch_pop):
        """Test sync-all command."""
        mock_sync_bls.return_value = None
        mock_fetch_pop.return_value = True
        
        try:
            main()
        except SystemExit:
            pass
        
        mock_sync_bls.assert_called_once_with('test-bucket', 'us-east-1')
        # When key is None, it's not passed to the function
        mock_fetch_pop.assert_called_once_with('test-bucket', 'us-east-1')
    
    @patch('sys.argv', ['cli.py'])
    @patch('sys.stdout', new_callable=StringIO)
    def test_no_command_prints_help(self, mock_stdout):
        """Test that no command prints help."""
        try:
            main()
        except SystemExit as e:
            assert e.code == 1  # argparse exits with code 1 for no command
    
    @patch('rearc.cli.sync_bls_data')
    @patch('sys.argv', ['cli.py', 'sync-bls', 'test-bucket'])
    def test_command_error_handling(self, mock_sync):
        """Test error handling in commands."""
        mock_sync.side_effect = Exception("Test error")
        
        try:
            main()
        except SystemExit as e:
            assert e.code == 1  # Should exit with error code


def run_all_tests():
    """Run all test classes."""
    logger.info("=" * 60)
    logger.info("Running CLI Test Suite")
    logger.info("=" * 60)
    
    test_classes = [
        TestCLI
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

