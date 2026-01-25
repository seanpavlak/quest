"""Analytics queries: population stats, best year per series, combined report."""

import logging
from typing import Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)


def query1_population_stats(population_df: pd.DataFrame) -> Dict[str, float]:
    """Mean and std dev of population for years 2013-2018."""
    logger.info("Query 1: Population Statistics (2013-2018)")
    if population_df.empty or 'Year' not in population_df.columns or 'Population' not in population_df.columns:
        logger.warning("Population data is empty or missing required columns (Year, Population)")
        return {'mean': 0, 'std_dev': 0}
    filtered_df = population_df[
        (population_df['Year'] >= 2013) & (population_df['Year'] <= 2018)
    ]
    
    if len(filtered_df) == 0:
        logger.warning("No population data found for years 2013-2018")
        return {'mean': 0, 'std_dev': 0}
    mean_pop = filtered_df['Population'].mean()
    std_dev_pop = filtered_df['Population'].std()
    
    logger.info(f"Found {len(filtered_df)} records for years 2013-2018")
    logger.info(f"Mean: {mean_pop:,.0f}, Std Dev: {std_dev_pop:,.0f}")
    
    return {
        'mean': float(mean_pop),
        'std_dev': float(std_dev_pop)
    }


def query2_best_year_per_series(bls_df: pd.DataFrame) -> pd.DataFrame:
    """For each series_id, return the year with the highest sum of values."""
    logger.info("Query 2: Best Year per Series ID")
    bls_df = bls_df.copy()
    bls_df.columns = bls_df.columns.str.strip()
    bls_df['series_id'] = bls_df['series_id'].str.strip()
    bls_df['value'] = pd.to_numeric(bls_df['value'], errors='coerce')
    yearly_sums = bls_df.groupby(['series_id', 'year'])['value'].sum().reset_index()
    yearly_sums.columns = ['series_id', 'year', 'sum_value']
    best_years = yearly_sums.loc[
        yearly_sums.groupby('series_id')['sum_value'].idxmax()
    ].copy()
    best_years = best_years[['series_id', 'year', 'sum_value']]
    best_years.columns = ['series_id', 'year', 'value']
    
    logger.info(f"Found best year for {len(best_years)} series")
    
    return best_years


def query3_combined_report(
    bls_df: pd.DataFrame,
    population_df: pd.DataFrame
) -> pd.DataFrame:
    """PRS30006032 Q01 BLS data joined with population by year."""
    logger.info("Query 3: Combined Report")
    bls_df = bls_df.copy()
    bls_df.columns = bls_df.columns.str.strip()
    bls_df['series_id'] = bls_df['series_id'].str.strip()
    bls_df['period'] = bls_df['period'].str.strip()
    bls_df['value'] = pd.to_numeric(bls_df['value'], errors='coerce')
    filtered_bls = bls_df[
        (bls_df['series_id'] == 'PRS30006032') & 
        (bls_df['period'] == 'Q01')
    ].copy()
    
    if len(filtered_bls) == 0:
        logger.warning("No data found for PRS30006032 Q01")
        return pd.DataFrame(columns=['series_id', 'year', 'period', 'value', 'Population'])
    if population_df.empty or 'Year' not in population_df.columns or 'Population' not in population_df.columns:
        logger.warning("Population data is empty or missing Year/Population; returning BLS data with null Population")
        filtered_bls = filtered_bls.copy()
        filtered_bls['Population'] = pd.NA
        return filtered_bls[['series_id', 'year', 'period', 'value', 'Population']]
    pop_for_join = population_df[['Year', 'Population']].copy()
    pop_for_join.columns = ['year', 'Population']
    result = filtered_bls.merge(pop_for_join, on='year', how='left')
    result = result[['series_id', 'year', 'period', 'value', 'Population']]
    
    logger.info(f"Found {len(result)} records for PRS30006032 Q01")
    logger.info(f"Records with population data: {result['Population'].notna().sum()}")
    
    return result

