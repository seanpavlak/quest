"""
Unit tests for Analytics queries.
Tests all three analytical queries with various edge cases.
"""
import sys
from pathlib import Path
import logging
import pandas as pd
import numpy as np
from unittest.mock import Mock

# Add src to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / 'src'))

from rearc.analytics.queries import (
    query1_population_stats,
    query2_best_year_per_series,
    query3_combined_report
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestQuery1PopulationStats:
    """Test Query 1: Population statistics."""
    
    def test_query1_normal_case(self):
        """Test normal case with valid data."""
        data = [
            {'Year': 2013, 'Population': 316128839},
            {'Year': 2014, 'Population': 318857056},
            {'Year': 2015, 'Population': 321418821},
            {'Year': 2016, 'Population': 323127515},
            {'Year': 2017, 'Population': 325719178},
            {'Year': 2018, 'Population': 327167439},
        ]
        df = pd.DataFrame(data)
        
        result = query1_population_stats(df)
        
        assert 'mean' in result
        assert 'std_dev' in result
        assert result['mean'] > 0
        assert result['std_dev'] >= 0
    
    def test_query1_filtered_years(self):
        """Test that only years 2013-2018 are included."""
        data = [
            {'Year': 2012, 'Population': 313000000},  # Should be excluded
            {'Year': 2013, 'Population': 316128839},
            {'Year': 2018, 'Population': 327167439},
            {'Year': 2019, 'Population': 328239523},  # Should be excluded
        ]
        df = pd.DataFrame(data)
        
        result = query1_population_stats(df)
        
        # Should only use 2013-2018 data
        assert result['mean'] == (316128839 + 327167439) / 2
    
    def test_query1_no_data(self):
        """Test with no data for years 2013-2018."""
        data = [
            {'Year': 2010, 'Population': 309000000},
            {'Year': 2020, 'Population': 331000000},
        ]
        df = pd.DataFrame(data)
        
        result = query1_population_stats(df)
        
        assert result['mean'] == 0
        assert result['std_dev'] == 0
    
    def test_query1_single_year(self):
        """Test with single year data."""
        data = [{'Year': 2015, 'Population': 321418821}]
        df = pd.DataFrame(data)
        
        result = query1_population_stats(df)
        
        assert result['mean'] == 321418821
        # Single value: std dev is NaN (pandas behavior) or 0, both are acceptable
        assert result['std_dev'] == 0 or pd.isna(result['std_dev'])


class TestQuery2BestYearPerSeries:
    """Test Query 2: Best year per series."""
    
    def test_query2_normal_case(self):
        """Test normal case with multiple series and years."""
        data = {
            'series_id': ['PRS30006011', 'PRS30006011', 'PRS30006011', 'PRS30006011',
                         'PRS30006012', 'PRS30006012', 'PRS30006012', 'PRS30006012'],
            'year': [1995, 1995, 1996, 1996, 2000, 2000, 2001, 2001],
            'period': ['Q01', 'Q02', 'Q01', 'Q02', 'Q01', 'Q02', 'Q01', 'Q02'],
            'value': [1, 2, 3, 4, 0, 8, 2, 3]
        }
        df = pd.DataFrame(data)
        
        result = query2_best_year_per_series(df)
        
        assert len(result) == 2
        assert 'series_id' in result.columns
        assert 'year' in result.columns
        assert 'value' in result.columns
        
        # PRS30006011: 1995 sum=3, 1996 sum=7 -> best year 1996
        # PRS30006012: 2000 sum=8, 2001 sum=5 -> best year 2000
        prs1 = result[result['series_id'] == 'PRS30006011'].iloc[0]
        prs2 = result[result['series_id'] == 'PRS30006012'].iloc[0]
        assert prs1['year'] == 1996
        assert prs1['value'] == 7
        assert prs2['year'] == 2000
        assert prs2['value'] == 8
    
    def test_query2_with_whitespace(self):
        """Test with whitespace in series_id (should be trimmed)."""
        data = {
            'series_id': [' PRS30006011 ', ' PRS30006011 ', 'PRS30006011', 'PRS30006011'],
            'year': [1995, 1995, 1996, 1996],
            'value': [1, 2, 3, 4]
        }
        df = pd.DataFrame(data)
        df.columns = [c.strip() for c in df.columns]  # Simulate column name trimming
        
        result = query2_best_year_per_series(df)
        
        assert len(result) == 1
        assert result.iloc[0]['series_id'] == 'PRS30006011'  # Should be trimmed
    
    def test_query2_single_series(self):
        """Test with single series."""
        data = {
            'series_id': ['PRS30006011', 'PRS30006011'],
            'year': [1995, 1996],
            'value': [5, 10]
        }
        df = pd.DataFrame(data)
        
        result = query2_best_year_per_series(df)
        
        assert len(result) == 1
        assert result.iloc[0]['year'] == 1996
        assert result.iloc[0]['value'] == 10
    
    def test_query2_empty_dataframe(self):
        """Test with empty dataframe."""
        df = pd.DataFrame(columns=['series_id', 'year', 'value'])
        
        result = query2_best_year_per_series(df)
        
        assert len(result) == 0


class TestQuery3CombinedReport:
    """Test Query 3: Combined report."""
    
    def test_query3_normal_case(self):
        """Test normal case with matching data."""
        bls_data = {
            'series_id': ['PRS30006032', 'PRS30006032', 'PRS30006032'],
            'year': [2013, 2014, 2015],
            'period': ['Q01', 'Q01', 'Q01'],
            'value': [0.5, -0.1, -1.7]
        }
        bls_df = pd.DataFrame(bls_data)
        
        pop_data = {
            'Year': [2013, 2014, 2015, 2016],
            'Population': [316128839, 318857056, 321418821, 323127515]
        }
        pop_df = pd.DataFrame(pop_data)
        
        result = query3_combined_report(bls_df, pop_df)
        
        assert len(result) == 3
        assert 'series_id' in result.columns
        assert 'year' in result.columns
        assert 'period' in result.columns
        assert 'value' in result.columns
        assert 'Population' in result.columns
        
        # Check that population data is joined correctly
        assert result[result['year'] == 2013]['Population'].iloc[0] == 316128839
        assert result[result['year'] == 2014]['Population'].iloc[0] == 318857056
    
    def test_query3_no_matching_population(self):
        """Test when population data doesn't have matching years."""
        bls_data = {
            'series_id': ['PRS30006032', 'PRS30006032'],
            'year': [2010, 2011],  # Years not in population data
            'period': ['Q01', 'Q01'],
            'value': [0.5, -0.1]
        }
        bls_df = pd.DataFrame(bls_data)
        
        pop_data = {
            'Year': [2013, 2014],
            'Population': [316128839, 318857056]
        }
        pop_df = pd.DataFrame(pop_data)
        
        result = query3_combined_report(bls_df, pop_df)
        
        assert len(result) == 2
        # Population should be NaN for non-matching years
        assert pd.isna(result['Population']).all()
    
    def test_query3_wrong_series_id(self):
        """Test filtering for only PRS30006032."""
        bls_data = {
            'series_id': ['PRS30006032', 'PRS30006011', 'PRS30006032'],  # Mixed series
            'year': [2013, 2013, 2014],
            'period': ['Q01', 'Q01', 'Q01'],
            'value': [0.5, 1.0, -0.1]
        }
        bls_df = pd.DataFrame(bls_data)
        
        pop_data = {
            'Year': [2013, 2014],
            'Population': [316128839, 318857056]
        }
        pop_df = pd.DataFrame(pop_data)
        
        result = query3_combined_report(bls_df, pop_df)
        
        # Should only include PRS30006032 records
        assert len(result) == 2
        assert (result['series_id'] == 'PRS30006032').all()
    
    def test_query3_wrong_period(self):
        """Test filtering for only Q01 period."""
        bls_data = {
            'series_id': ['PRS30006032', 'PRS30006032', 'PRS30006032'],
            'year': [2013, 2013, 2014],
            'period': ['Q01', 'Q02', 'Q01'],  # Mixed periods
            'value': [0.5, 0.2, -0.1]
        }
        bls_df = pd.DataFrame(bls_data)
        
        pop_data = {
            'Year': [2013, 2014],
            'Population': [316128839, 318857056]
        }
        pop_df = pd.DataFrame(pop_data)
        
        result = query3_combined_report(bls_df, pop_df)
        
        # Should only include Q01 records
        assert len(result) == 2
        assert (result['period'] == 'Q01').all()
    
    def test_query3_no_data(self):
        """Test with no matching data."""
        bls_data = {
            'series_id': ['PRS30006011'],  # Wrong series_id
            'year': [2013],
            'period': ['Q01'],
            'value': [0.5]
        }
        bls_df = pd.DataFrame(bls_data)
        
        pop_data = {
            'Year': [2013],
            'Population': [316128839]
        }
        pop_df = pd.DataFrame(pop_data)
        
        result = query3_combined_report(bls_df, pop_df)
        
        assert len(result) == 0
        assert list(result.columns) == ['series_id', 'year', 'period', 'value', 'Population']


def run_all_tests():
    """Run all test classes."""
    logger.info("=" * 60)
    logger.info("Running Analytics Queries Test Suite")
    logger.info("=" * 60)
    
    test_classes = [
        TestQuery1PopulationStats,
        TestQuery2BestYearPerSeries,
        TestQuery3CombinedReport
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

