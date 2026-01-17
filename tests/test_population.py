"""
Unit tests for Population API functions.
Tests API fetching, S3 saving, and error handling.
"""
import sys
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.data_sync.population import (
    fetch_population_data,
    save_to_s3,
    fetch_and_save_population_data,
    DATAUSA_API_URL,
    POPULATION_FILE_PREFIX,
)


class TestFetchPopulationData:
    """Test population data fetching from API."""
    
    @patch('rearc.data_sync.population.requests.get')
    def test_fetch_population_data_success(self, mock_get: Mock) -> None:
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
        mock_get.assert_called_once()
    
    @patch('rearc.data_sync.population.requests.get')
    def test_fetch_population_data_http_error(self, mock_get: Mock) -> None:
        """Test API fetch with HTTP error."""
        import requests
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        result = fetch_population_data('https://example.com/api')
        
        assert result is None
    
    @patch('rearc.data_sync.population.requests.get')
    def test_fetch_population_data_invalid_json(self, mock_get: Mock) -> None:
        """Test API fetch with invalid JSON."""
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
    def test_save_to_s3_success(self, mock_boto3_client: Mock) -> None:
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
    def test_save_to_s3_timestamp_key(self, mock_boto3_client: Mock) -> None:
        """Test save with timestamp-based key."""
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        test_data = {'data': []}
        
        result = save_to_s3('test-bucket', test_data, None, 'us-east-1')
        
        assert result is True
        call_args = mock_s3_client.put_object.call_args
        key = call_args[1]['Key']
        assert key.startswith(POPULATION_FILE_PREFIX)
        assert key.endswith('.json')
    
    @patch('rearc.data_sync.population.boto3.client')
    def test_save_to_s3_error(self, mock_boto3_client: Mock) -> None:
        """Test save with S3 error."""
        from botocore.exceptions import ClientError
        mock_s3_client = Mock()
        error_response = {'Error': {'Code': 'AccessDenied'}}
        mock_s3_client.put_object.side_effect = ClientError(error_response, 'put_object')
        mock_boto3_client.return_value = mock_s3_client
        
        test_data = {'data': []}
        
        result = save_to_s3('test-bucket', test_data, 'test-key.json', 'us-east-1')
        
        assert result is False


class TestFetchAndSavePopulationData:
    """Test full fetch and save workflow."""
    
    @patch('rearc.data_sync.population.save_to_s3')
    @patch('rearc.data_sync.population.fetch_population_data')
    def test_fetch_and_save_success(
        self,
        mock_fetch: Mock,
        mock_save: Mock
    ) -> None:
        """Test successful fetch and save."""
        mock_fetch.return_value = {'data': [{'Year': 2013, 'Population': 316128839}]}
        mock_save.return_value = True
        
        result = fetch_and_save_population_data('test-bucket', 'us-east-1', 'test-key.json')
        
        assert result is True
        mock_fetch.assert_called_once()
        mock_save.assert_called_once()
    
    @patch('rearc.data_sync.population.save_to_s3')
    @patch('rearc.data_sync.population.fetch_population_data')
    def test_fetch_and_save_fetch_fails(
        self,
        mock_fetch: Mock,
        mock_save: Mock
    ) -> None:
        """Test fetch and save when fetch fails."""
        mock_fetch.return_value = None
        
        result = fetch_and_save_population_data('test-bucket', 'us-east-1')
        
        assert result is False
        mock_fetch.assert_called_once()
        mock_save.assert_not_called()
    
    @patch('rearc.data_sync.population.save_to_s3')
    @patch('rearc.data_sync.population.fetch_population_data')
    def test_fetch_and_save_save_fails(
        self,
        mock_fetch: Mock,
        mock_save: Mock
    ) -> None:
        """Test fetch and save when save fails."""
        mock_fetch.return_value = {'data': []}
        mock_save.return_value = False
        
        result = fetch_and_save_population_data('test-bucket', 'us-east-1')
        
        assert result is False
        mock_fetch.assert_called_once()
        mock_save.assert_called_once()
