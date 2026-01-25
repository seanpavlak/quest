"""Local tests without AWS: BLS fetch, population fetch, analytics, S3 mock, directory discovery."""
import sys
from pathlib import Path
import logging
import json
import pandas as pd
from io import StringIO

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.data_sync.bls_parser import (
    fetch_url_content,
    parse_directory_listing,
    discover_files_and_directories,
)
from rearc.data_sync.bls_s3_ops import calculate_md5
from rearc.data_sync.bls_sync import BLS_BASE_URL
from rearc.data_sync.population import fetch_population_data
from rearc.analytics.queries import (
    query1_population_stats,
    query2_best_year_per_series,
    query3_combined_report
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'local'
DATA_DIR.mkdir(parents=True, exist_ok=True)


def test_bls_fetch():
    logger.info("=" * 60)
    logger.info("TEST 1: Fetching BLS Data")
    logger.info("=" * 60)
    
    url = "https://download.bls.gov/pub/time.series/pr/pr.data.0.Current"
    content = fetch_url_content(url)
    
    if content:
        logger.info(f"✓ Successfully fetched {len(content)} bytes")
        output_file = DATA_DIR / "pr.data.0.Current"
        output_file.write_bytes(content)
        logger.info(f"✓ Saved to {output_file}")
        md5 = calculate_md5(content)
        logger.info(f"✓ MD5: {md5}")
        
        return True, content
    else:
        logger.error("✗ Failed to fetch BLS data")
        return False, None


def test_population_fetch():
    logger.info("=" * 60)
    logger.info("TEST 2: Fetching Population Data")
    logger.info("=" * 60)
    
    api_url = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"
    data = fetch_population_data(api_url)
    
    if data:
        logger.info(f"✓ Successfully fetched data")
        logger.info(f"✓ Keys: {list(data.keys())}")
        logger.info(f"✓ Records: {len(data.get('data', []))}")
        output_file = DATA_DIR / "population_data.json"
        output_file.write_text(json.dumps(data, indent=2))
        logger.info(f"✓ Saved to {output_file}")
        
        return True, data
    else:
        logger.error("✗ Failed to fetch population data")
        return False, None


def test_analytics_queries():
    logger.info("=" * 60)
    logger.info("TEST 3: Analytics Queries")
    logger.info("=" * 60)
    bls_file = DATA_DIR / "pr.data.0.Current"
    if not bls_file.exists():
        logger.error("✗ BLS data file not found. Run test_bls_fetch() first.")
        return False
    
    bls_content = bls_file.read_text()
    bls_df = pd.read_csv(StringIO(bls_content), sep='\t')
    bls_df.columns = bls_df.columns.str.strip()
    string_columns = bls_df.select_dtypes(include=['object']).columns
    for col in string_columns:
        if col != 'footnote_codes':
            bls_df[col] = bls_df[col].str.strip()
    logger.info(f"✓ Loaded BLS data: {bls_df.shape}")
    logger.info(f"✓ Columns: {bls_df.columns.tolist()}")
    pop_file = DATA_DIR / "population_data.json"
    if not pop_file.exists():
        logger.error("✗ Population data file not found. Run test_population_fetch() first.")
        return False
    
    pop_data = json.loads(pop_file.read_text())
    population_df = pd.DataFrame(pop_data.get('data', []))
    
    logger.info(f"✓ Loaded population data: {population_df.shape}")
    logger.info(f"✓ Columns: {population_df.columns.tolist()}")
    logger.info("\n--- Query 1: Population Statistics (2013-2018) ---")
    result1 = query1_population_stats(population_df)
    logger.info(f"Result: {result1}")
    logger.info("\n--- Query 2: Best Year per Series ID ---")
    result2 = query2_best_year_per_series(bls_df)
    logger.info(f"Result shape: {result2.shape}")
    if len(result2) > 0:
        logger.info(f"First few rows:\n{result2.head()}")
    logger.info("\n--- Query 3: Combined Report ---")
    result3 = query3_combined_report(bls_df, population_df)
    logger.info(f"Result shape: {result3.shape}")
    if len(result3) > 0:
        logger.info(f"First few rows:\n{result3.head()}")
    
    return True


def test_bls_directory_discovery():
    logger.info("=" * 60)
    logger.info("TEST 5: BLS Directory Discovery")
    logger.info("=" * 60)
    try:
        test_html = """
        <html><body><table>
        <tr><td><a href="pr.data.0.Current">pr.data.0.Current</a></td></tr>
        <tr><td><a href="pr.series">pr.series</a></td></tr>
        <tr><td><a href="data/">data/</a></td></tr>
        </table></body></html>
        """
        
        files, directories = parse_directory_listing(test_html)
        
        assert 'pr.data.0.Current' in files
        assert 'pr.series' in files
        assert 'data' in directories
        logger.info("✓ HTML parsing works correctly")
        try:
            files, dirs = discover_files_and_directories(BLS_BASE_URL, '')
            if files or dirs:
                logger.info(f"✓ Discovered {len(files)} files and {len(dirs)} directories")
                logger.info(f"  Sample files: {files[:3]}")
                logger.info(f"  Sample dirs: {dirs[:3]}")
            else:
                logger.warning("⚠ No files/directories discovered (may be network issue)")
        except Exception as e:
            logger.warning(f"⚠ Could not test actual discovery: {e}")
        return True
    except Exception as e:
        logger.error(f"✗ Directory discovery test failed: {e}")
        return False


def test_with_local_s3_mock():
    try:
        from moto import mock_s3
        import boto3
        
        logger.info("=" * 60)
        logger.info("TEST 4: S3 Operations (Mocked)")
        logger.info("=" * 60)
        
        with mock_s3():
            s3_client = boto3.client('s3', region_name='us-east-1')
            bucket_name = 'test-bucket'
            s3_client.create_bucket(Bucket=bucket_name)
            logger.info(f"✓ Created mock bucket: {bucket_name}")
            test_content = b"test data"
            s3_client.put_object(Bucket=bucket_name, Key='test.txt', Body=test_content)
            logger.info("✓ Uploaded test file")
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
    logger.info("Starting Local Tests")
    logger.info(f"Data will be saved to: {DATA_DIR}")
    results = {}
    results['bls'] = test_bls_fetch()
    results['population'] = test_population_fetch()
    if results['bls'][0] and results['population'][0]:
        results['analytics'] = test_analytics_queries()
    else:
        logger.warning("Skipping analytics tests - data fetch failed")
        results['analytics'] = False
    results['s3_mock'] = test_with_local_s3_mock()
    results['bls_discovery'] = test_bls_directory_discovery()
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL" if result is False else "⊘ SKIP"
        logger.info(f"{test_name:20} {status}")
    non_skipped = [r for r in results.values() if r is not None]
    return all(non_skipped) if non_skipped else False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

