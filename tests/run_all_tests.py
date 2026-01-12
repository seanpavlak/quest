#!/usr/bin/env python3
"""
Run all tests locally without AWS.

This script runs the complete test suite:
- Unit tests (BLS sync, Population API, CLI)
- Integration tests (local data fetching and analytics)

Usage:
    python tests/run_all_tests.py
"""
import sys
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test files to run (in order)
TEST_FILES = [
    'tests/test_bls_sync.py',      # Unit tests: BLS sync
    'tests/test_population.py',    # Unit tests: Population API
    'tests/test_analytics.py',     # Unit tests: Analytics queries
    'tests/test_cli.py',           # Unit tests: CLI
    'tests/test_local.py',         # Integration tests (requires network)
]


def run_test_file(test_file):
    """Run a single test file and return success status."""
    logger.info("=" * 70)
    logger.info(f"Running: {test_file}")
    logger.info("=" * 70)
    
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=False,
            text=True,
            check=True
        )
        logger.info(f"✅ {test_file} - PASSED")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {test_file} - FAILED (exit code: {e.returncode})")
        return False
    except FileNotFoundError:
        logger.error(f"❌ {test_file} - NOT FOUND")
        return False


def main():
    """Run all test files."""
    logger.info("=" * 70)
    logger.info("Running Complete Test Suite (Local - No AWS Required)")
    logger.info("=" * 70)
    logger.info("")
    logger.info("This will run:")
    logger.info("  1. Unit tests for BLS sync")
    logger.info("  2. Unit tests for Population API")
    logger.info("  3. Unit tests for Analytics queries")
    logger.info("  4. Unit tests for CLI")
    logger.info("  5. Integration tests (requires network for data fetching)")
    logger.info("")
    
    # Check if we're in the right directory
    if not Path('tests').exists():
        logger.error("Error: Must run from project root directory")
        sys.exit(1)
    
    results = {}
    
    for test_file in TEST_FILES:
        if not Path(test_file).exists():
            logger.warning(f"⚠️  {test_file} not found, skipping")
            results[test_file] = None
            continue
        
        success = run_test_file(test_file)
        results[test_file] = success
        logger.info("")
    
    # Summary
    logger.info("=" * 70)
    logger.info("TEST SUITE SUMMARY")
    logger.info("=" * 70)
    
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)
    
    for test_file, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"
        logger.info(f"{status} - {test_file}")
    
    logger.info("=" * 70)
    logger.info(f"Total: {total}, Passed: {passed}, Failed: {failed}, Skipped: {skipped}")
    logger.info("=" * 70)
    
    if failed > 0:
        logger.error("Some tests failed!")
        sys.exit(1)
    elif passed == total:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.warning("Some tests were skipped")
        sys.exit(0)


if __name__ == '__main__':
    main()

