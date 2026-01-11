"""
Analytics Queries Module

Contains the three analytical queries for the data pipeline.
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


def query1_population_stats(population_df: pd.DataFrame) -> dict:
    """
    Query 1: Calculate mean and standard deviation of US population (2013-2018).
    
    Args:
        population_df: DataFrame containing population data
        
    Returns:
        dict with 'mean' and 'std_dev' keys
    """
    logger.info("Query 1: Population Statistics (2013-2018)")
    
    # Filter for years 2013-2018 (inclusive)
    # Population data has 'Year' column (capital Y)
    filtered_df = population_df[
        (population_df['Year'] >= 2013) & (population_df['Year'] <= 2018)
    ]
    
    if len(filtered_df) == 0:
        logger.warning("No population data found for years 2013-2018")
        return {'mean': 0, 'std_dev': 0}
    
    # Calculate mean and standard deviation
    mean_pop = filtered_df['Population'].mean()
    std_dev_pop = filtered_df['Population'].std()
    
    logger.info(f"Found {len(filtered_df)} records for years 2013-2018")
    logger.info(f"Mean: {mean_pop:,.0f}, Std Dev: {std_dev_pop:,.0f}")
    
    return {
        'mean': float(mean_pop),
        'std_dev': float(std_dev_pop)
    }


def query2_best_year_per_series(bls_df: pd.DataFrame) -> pd.DataFrame:
    """
    Query 2: Find best year per series_id (year with max sum of values).
    
    Args:
        bls_df: DataFrame containing BLS time-series data
        
    Returns:
        DataFrame with columns: series_id, year, value
    """
    logger.info("Query 2: Best Year per Series ID")
    
    # Clean column names (remove extra spaces)
    bls_df = bls_df.copy()
    bls_df.columns = bls_df.columns.str.strip()
    
    # Trim string values in series_id column
    bls_df['series_id'] = bls_df['series_id'].str.strip()
    
    # Ensure value column is numeric
    bls_df['value'] = pd.to_numeric(bls_df['value'], errors='coerce')
    
    # Group by series_id and year, sum values for all quarters in that year
    yearly_sums = bls_df.groupby(['series_id', 'year'])['value'].sum().reset_index()
    yearly_sums.columns = ['series_id', 'year', 'sum_value']
    
    # Find the year with maximum sum for each series_id
    best_years = yearly_sums.loc[
        yearly_sums.groupby('series_id')['sum_value'].idxmax()
    ].copy()
    
    # Rename sum_value to value for output
    best_years = best_years[['series_id', 'year', 'sum_value']]
    best_years.columns = ['series_id', 'year', 'value']
    
    logger.info(f"Found best year for {len(best_years)} series")
    
    return best_years


def query3_combined_report(bls_df: pd.DataFrame, population_df: pd.DataFrame) -> pd.DataFrame:
    """
    Query 3: Combined report for PRS30006032 Q01 with population data.
    
    Args:
        bls_df: DataFrame containing BLS time-series data
        population_df: DataFrame containing population data
        
    Returns:
        DataFrame with columns: series_id, year, period, value, Population
    """
    logger.info("Query 3: Combined Report")
    
    # Clean BLS column names (remove extra spaces)
    bls_df = bls_df.copy()
    bls_df.columns = bls_df.columns.str.strip()
    
    # Trim string values in series_id and period columns
    bls_df['series_id'] = bls_df['series_id'].str.strip()
    bls_df['period'] = bls_df['period'].str.strip()
    
    # Ensure value column is numeric
    bls_df['value'] = pd.to_numeric(bls_df['value'], errors='coerce')
    
    # Filter for series_id = PRS30006032 and period = Q01
    filtered_bls = bls_df[
        (bls_df['series_id'] == 'PRS30006032') & 
        (bls_df['period'] == 'Q01')
    ].copy()
    
    if len(filtered_bls) == 0:
        logger.warning("No data found for PRS30006032 Q01")
        return pd.DataFrame(columns=['series_id', 'year', 'period', 'value', 'Population'])
    
    # Prepare population data for join (rename Year to year for consistency)
    pop_for_join = population_df[['Year', 'Population']].copy()
    pop_for_join.columns = ['year', 'Population']
    
    # Join BLS data with population data on year
    result = filtered_bls.merge(
        pop_for_join,
        on='year',
        how='left'  # Left join to keep all BLS records even if population data missing
    )
    
    # Select and order columns
    result = result[['series_id', 'year', 'period', 'value', 'Population']]
    
    logger.info(f"Found {len(result)} records for PRS30006032 Q01")
    logger.info(f"Records with population data: {result['Population'].notna().sum()}")
    
    return result

