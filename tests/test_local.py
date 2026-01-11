"""
Local testing script - tests all functionality without AWS
"""
import sys
from pathlib import Path
import logging
import json
import pandas as pd
from io import StringIO

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.data_sync.bls import fetch_url_content, calculate_md5
from rearc.data_sync.population import fetch_population_data
from rearc.analytics.queries import (
    query1_population_stats,
    query2_best_year_per_series,
    query3_combined_report
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Local data directory
DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'local'
DATA_DIR.mkdir(parents=True, exist_ok=True)


def test_bls_fetch():
    """Test fetching BLS data."""
    logger.info("=" * 60)
    logger.info("TEST 1: Fetching BLS Data")
    logger.info("=" * 60)
    
    url = "https://download.bls.gov/pub/time.series/pr/pr.data.0.Current"
    content = fetch_url_content(url)
    
    if content:
        logger.info(f"✓ Successfully fetched {len(content)} bytes")
        
        # Save to local file
        output_file = DATA_DIR / "pr.data.0.Current"
        output_file.write_bytes(content)
        logger.info(f"✓ Saved to {output_file}")
        
        # Calculate hash
        md5 = calculate_md5(content)
        logger.info(f"✓ MD5: {md5}")
        
        return True, content
    else:
        logger.error("✗ Failed to fetch BLS data")
        return False, None


def test_population_fetch():
    """Test fetching population data."""
    logger.info("=" * 60)
    logger.info("TEST 2: Fetching Population Data")
    logger.info("=" * 60)
    
    api_url = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"
    data = fetch_population_data(api_url)
    
    if data:
        logger.info(f"✓ Successfully fetched data")
        logger.info(f"✓ Keys: {list(data.keys())}")
        logger.info(f"✓ Records: {len(data.get('data', []))}")
        
        # Save to local file
        output_file = DATA_DIR / "population_data.json"
        output_file.write_text(json.dumps(data, indent=2))
        logger.info(f"✓ Saved to {output_file}")
        
        return True, data
    else:
        logger.error("✗ Failed to fetch population data")
        return False, None


def test_analytics_queries():
    """Test analytics queries with local data."""
    logger.info("=" * 60)
    logger.info("TEST 3: Analytics Queries")
    logger.info("=" * 60)
    
    # Load BLS data
    bls_file = DATA_DIR / "pr.data.0.Current"
    if not bls_file.exists():
        logger.error("✗ BLS data file not found. Run test_bls_fetch() first.")
        return False
    
    bls_content = bls_file.read_text()
    bls_df = pd.read_csv(StringIO(bls_content), sep='\t')
    
    # Clean BLS data - trim column names and string values
    bls_df.columns = bls_df.columns.str.strip()
    string_columns = bls_df.select_dtypes(include=['object']).columns
    for col in string_columns:
        if col != 'footnote_codes':  # Skip footnote_codes which may have NaN
            bls_df[col] = bls_df[col].str.strip()
    
    logger.info(f"✓ Loaded BLS data: {bls_df.shape}")
    logger.info(f"✓ Columns: {bls_df.columns.tolist()}")
    
    # Load population data
    pop_file = DATA_DIR / "population_data.json"
    if not pop_file.exists():
        logger.error("✗ Population data file not found. Run test_population_fetch() first.")
        return False
    
    pop_data = json.loads(pop_file.read_text())
    population_df = pd.DataFrame(pop_data.get('data', []))
    
    logger.info(f"✓ Loaded population data: {population_df.shape}")
    logger.info(f"✓ Columns: {population_df.columns.tolist()}")
    
    # Test Query 1
    logger.info("\n--- Query 1: Population Statistics (2013-2018) ---")
    result1 = query1_population_stats(population_df)
    logger.info(f"Result: {result1}")
    
    # Test Query 2
    logger.info("\n--- Query 2: Best Year per Series ID ---")
    result2 = query2_best_year_per_series(bls_df)
    logger.info(f"Result shape: {result2.shape}")
    if len(result2) > 0:
        logger.info(f"First few rows:\n{result2.head()}")
    
    # Test Query 3
    logger.info("\n--- Query 3: Combined Report ---")
    result3 = query3_combined_report(bls_df, population_df)
    logger.info(f"Result shape: {result3.shape}")
    if len(result3) > 0:
        logger.info(f"First few rows:\n{result3.head()}")
    
    return True


def test_with_local_s3_mock():
    """Test with mocked S3 using moto (optional)."""
    try:
        from moto import mock_s3
        import boto3
        
        logger.info("=" * 60)
        logger.info("TEST 4: S3 Operations (Mocked)")
        logger.info("=" * 60)
        
        with mock_s3():
            s3_client = boto3.client('s3', region_name='us-east-1')
            bucket_name = 'test-bucket'
            
            # Create bucket
            s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"✓ Created mock bucket: {bucket_name}")
            
            # Upload test file
            test_content = b"test data"
            s3_client.put_object(Bucket=bucket_name, Key='test.txt', Body=test_content)
            logger.info("✓ Uploaded test file")
            
            # Download test file
            response = s3_client.get_object(Bucket=bucket_name, Key='test.txt')
            downloaded = response['Body'].read()
            assert downloaded == test_content
            logger.info("✓ Downloaded and verified test file")
            
            return True
    except ImportError:
        logger.warning("moto not installed. Skipping S3 mock test.")
        logger.info("Install with: pip install moto")
        return None


def main():
    """Run all tests."""
    logger.info("Starting Local Tests")
    logger.info(f"Data will be saved to: {DATA_DIR}")
    
    results = {}
    
    # Test 1: BLS fetch
    results['bls'] = test_bls_fetch()
    
    # Test 2: Population fetch
    results['population'] = test_population_fetch()
    
    # Test 3: Analytics queries
    if results['bls'][0] and results['population'][0]:
        results['analytics'] = test_analytics_queries()
    else:
        logger.warning("Skipping analytics tests - data fetch failed")
        results['analytics'] = False
    
    # Test 4: S3 mock (optional)
    results['s3_mock'] = test_with_local_s3_mock()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL" if result is False else "⊘ SKIP"
        logger.info(f"{test_name:20} {status}")
    
    return all(r for r in results.values() if r is not False)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

