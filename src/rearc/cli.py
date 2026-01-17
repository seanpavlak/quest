"""
Command-line interface for the Rearc Data Quest pipeline.
"""

import argparse
import logging
import sys
from typing import NoReturn

from .data_sync import sync_bls_data, fetch_and_save_population_data

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description='Rearc Data Quest Pipeline')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # BLS sync command
    bls_parser = subparsers.add_parser('sync-bls', help='Sync BLS data to S3')
    bls_parser.add_argument('bucket', help='S3 bucket name')
    bls_parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    # Population fetch command
    pop_parser = subparsers.add_parser('fetch-population', help='Fetch population data and save to S3')
    pop_parser.add_argument('bucket', help='S3 bucket name')
    pop_parser.add_argument('--region', default='us-east-1', help='AWS region')
    pop_parser.add_argument('--key', help='S3 object key (optional)')
    
    # Sync all command
    all_parser = subparsers.add_parser('sync-all', help='Sync both BLS and population data')
    all_parser.add_argument('bucket', help='S3 bucket name')
    all_parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    try:
        if args.command == 'sync-bls':
            success = sync_bls_data(args.bucket, args.region)
            if not success:
                logger.error("BLS sync failed")
                sys.exit(1)
        elif args.command == 'fetch-population':
            success = fetch_and_save_population_data(args.bucket, args.region, args.key)
            if not success:
                logger.error("Population data fetch failed")
                sys.exit(1)
        elif args.command == 'sync-all':
            bls_success = sync_bls_data(args.bucket, args.region)
            pop_success = fetch_and_save_population_data(args.bucket, args.region)
            if not (bls_success and pop_success):
                logger.error("One or more sync operations failed")
                sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

