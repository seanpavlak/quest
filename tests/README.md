# Testing Guide

## Test Results Summary

✅ **All core tests passing!**

### Test 1: BLS Data Fetch
- ✓ Successfully fetches ~1.5MB of BLS time-series data
- ✓ Saves to `data/local/pr.data.0.Current`
- ✓ Calculates MD5 hash for change detection

### Test 2: Population Data Fetch
- ✓ Successfully fetches 10 records from DataUSA API
- ✓ Saves to `data/local/population_data.json`
- ✓ Data includes years 2013-2023

### Test 3: Analytics Queries
- ✓ Loads both datasets successfully
- ⚠️ Queries are placeholders (need implementation)
- Data structure confirmed:
  - **BLS**: `series_id`, `year`, `period`, `value`, `footnote_codes`
  - **Population**: `Nation ID`, `Nation`, `Year`, `Population`

### Test 4: S3 Mock (Optional)
- ⊘ Skipped (moto not installed)
- Install with: `pip install moto`

## Running Tests

### Simple Test (Just Fetch Data)
```bash
python scripts/test_local_simple.py
```

### Full Test Suite
```bash
python tests/test_local.py
```

## Data Structure

### BLS Data
- **File**: `data/local/pr.data.0.Current`
- **Format**: Tab-separated values
- **Columns**: `series_id`, `year`, `period`, `value`, `footnote_codes`
- **Note**: Columns have leading/trailing spaces that need trimming
- **Size**: ~37,521 rows

### Population Data
- **File**: `data/local/population_data.json`
- **Format**: JSON
- **Columns**: `Nation ID`, `Nation`, `Year`, `Population`
- **Years**: 2013-2023 (10 records)
- **All records**: United States

## Implementation Status

1. ✅ Data fetching works
2. ✅ Analytics queries implemented:
   - ✅ Query 1: Population stats (2013-2018) - Mean: 322,069,808, Std Dev: 4,158,441
   - ✅ Query 2: Best year per series_id - Found best year for 282 series
   - ✅ Query 3: Combined report (PRS30006032 Q01 + population) - 31 records, 10 with population data
3. ✅ Column name trimming fixed (column names and values)
4. ⊘ S3 mock test (optional - requires moto)

## Query Results

### Query 1: Population Statistics (2013-2018)
- **Mean**: 322,069,808
- **Standard Deviation**: 4,158,441
- **Records**: 6 years (2013-2018)

### Query 2: Best Year per Series ID
- **Total Series**: 282
- **Example**: PRS30006032 best year is 2021 with sum value of 17.1

### Query 3: Combined Report (PRS30006032 Q01 + Population)
- **Total Records**: 31 (all years with Q01 data)
- **Records with Population**: 10 (years 2013-2023 where population data exists)
- **Sample (2013-2018)**:
  - 2013 Q01: value=0.5, Population=316,128,839
  - 2014 Q01: value=-0.1, Population=318,857,056
  - 2015 Q01: value=-1.7, Population=321,418,821
  - 2016 Q01: value=-1.4, Population=323,127,515
  - 2017 Q01: value=0.9, Population=325,719,178
  - 2018 Q01: value=0.5, Population=327,167,439

