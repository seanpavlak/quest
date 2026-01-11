"""
Simple local test - just fetch data and save locally
"""
import sys
from pathlib import Path
import logging

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.data_sync.bls import fetch_url_content
from rearc.data_sync.population import fetch_population_data
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'local'
DATA_DIR.mkdir(parents=True, exist_ok=True)

def main():
    logger.info("Fetching BLS data...")
    url = "https://download.bls.gov/pub/time.series/pr/pr.data.0.Current"
    content = fetch_url_content(url)
    
    if content:
        output = DATA_DIR / "pr.data.0.Current"
        output.write_bytes(content)
        logger.info(f"✓ Saved BLS data to {output}")
    else:
        logger.error("Failed to fetch BLS data")
        return
    
    logger.info("Fetching population data...")
    api_url = "https://honolulu-api.datausa.io/tesseract/data.jsonrecords?cube=acs_yg_total_population_1&drilldowns=Year%2CNation&locale=en&measures=Population"
    data = fetch_population_data(api_url)
    
    if data:
        output = DATA_DIR / "population_data.json"
        output.write_text(json.dumps(data, indent=2))
        logger.info(f"✓ Saved population data to {output}")
    else:
        logger.error("Failed to fetch population data")
        return
    
    logger.info("✓ All data fetched successfully!")
    logger.info(f"Data saved to: {DATA_DIR}")

if __name__ == '__main__':
    main()

