"""
Unit tests for Population API functions.
Tests API fetching, S3 saving, and error handling.
"""
import sys
from pathlib import Path
import logging
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.data_sync.population import (
    fetch_population_data,
    save_to_s3,
    fetch_and_save_population_data,
    DATAUSA_API_URL
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestFetchPopulationData:
    """Test population data fetching from API."""
    
    @patch('rearc.data_sync.population.requests.get')
    def test_fetch_population_data_success(self, mock_get):
        """Test successful API fetch."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [
                {'Year': 2013, 'Nation': 'United States', 'Population': 316128839},
                {'Year': 2014, 'Nation': 'United States', 'Population': 318857056}
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_population_data('https://example.com/api')
        
        assert result is not None
        assert 'data' in result
        assert len(result['data']) == 2
        mock_get.assert_called_once_with('https://example.com/api', timeout=30)
    
    @patch('rearc.data_sync.population.requests.get')
    def test_fetch_population_data_http_error(self, mock_get):
        """Test API fetch with HTTP error."""
        import requests
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        result = fetch_population_data('https://example.com/api')
        
        assert result is None
    
    @patch('rearc.data_sync.population.requests.get')
    def test_fetch_population_data_invalid_json(self, mock_get):
        """Test API fetch with invalid JSON."""
        import requests
        import json
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        result = fetch_population_data('https://example.com/api')
        
        assert result is None


class TestSaveToS3:
    """Test saving population data to S3."""
    
    @patch('rearc.data_sync.population.boto3.client')
    def test_save_to_s3_success(self, mock_boto3_client):
        """Test successful save to S3."""
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        test_data = {'data': [{'Year': 2013, 'Population': 316128839}]}
        
        result = save_to_s3('test-bucket', test_data, 'test-key.json', 'us-east-1')
        
        assert result is True
        mock_s3_client.put_object.assert_called_once()
        call_args = mock_s3_client.put_object.call_args
        assert call_args[1]['Bucket'] == 'test-bucket'
        assert call_args[1]['Key'] == 'test-key.json'
        assert call_args[1]['ContentType'] == 'application/json'
    
    @patch('rearc.data_sync.population.boto3.client')
    def test_save_to_s3_timestamp_key(self, mock_boto3_client):
        """Test save with timestamp-based key."""
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        test_data = {'data': []}
        
        result = save_to_s3('test-bucket', test_data, None, 'us-east-1')
        
        assert result is True
        call_args = mock_s3_client.put_object.call_args
        key = call_args[1]['Key']
        assert key.startswith('population_data_')
        assert key.endswith('.json')
    
    @patch('rearc.data_sync.population.boto3.client')
    def test_save_to_s3_error(self, mock_boto3_client):
        """Test save with S3 error."""
        mock_s3_client = Mock()
        mock_s3_client.put_object.side_effect = Exception("S3 Error")
        mock_boto3_client.return_value = mock_s3_client
        
        test_data = {'data': []}
        
        result = save_to_s3('test-bucket', test_data, 'test-key.json', 'us-east-1')
        
        assert result is False


class TestFetchAndSavePopulationData:
    """Test full fetch and save workflow."""
    
    @patch('rearc.data_sync.population.save_to_s3')
    @patch('rearc.data_sync.population.fetch_population_data')
    def test_fetch_and_save_success(self, mock_fetch, mock_save):
        """Test successful fetch and save."""
        mock_fetch.return_value = {'data': [{'Year': 2013, 'Population': 316128839}]}
        mock_save.return_value = True
        
        result = fetch_and_save_population_data('test-bucket', 'us-east-1', 'test-key.json')
        
        assert result is True
        mock_fetch.assert_called_once()
        mock_save.assert_called_once()
    
    @patch('rearc.data_sync.population.save_to_s3')
    @patch('rearc.data_sync.population.fetch_population_data')
    def test_fetch_and_save_fetch_fails(self, mock_fetch, mock_save):
        """Test fetch and save when fetch fails."""
        mock_fetch.return_value = None
        
        result = fetch_and_save_population_data('test-bucket', 'us-east-1')
        
        assert result is False
        mock_fetch.assert_called_once()
        mock_save.assert_not_called()
    
    @patch('rearc.data_sync.population.save_to_s3')
    @patch('rearc.data_sync.population.fetch_population_data')
    def test_fetch_and_save_save_fails(self, mock_fetch, mock_save):
        """Test fetch and save when save fails."""
        mock_fetch.return_value = {'data': []}
        mock_save.return_value = False
        
        result = fetch_and_save_population_data('test-bucket', 'us-east-1')
        
        assert result is False
        mock_fetch.assert_called_once()
        mock_save.assert_called_once()


def run_all_tests():
    """Run all test classes."""
    logger.info("=" * 60)
    logger.info("Running Population API Test Suite")
    logger.info("=" * 60)
    
    test_classes = [
        TestFetchPopulationData,
        TestSaveToS3,
        TestFetchAndSavePopulationData
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

