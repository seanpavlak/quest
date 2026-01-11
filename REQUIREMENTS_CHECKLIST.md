# Requirements Checklist

## Part 1: AWS S3 & Sourcing Datasets

### ✅ Completed
- [x] Republish BLS dataset in S3
- [x] User-Agent header with contact info (complies with BLS policy)
- [x] MD5 checksum comparison (doesn't upload same file twice)
- [x] Upload functionality
- [x] Delete functionality (function exists)

### ✅ Completed
- [x] **Full directory traversal** - Recursively discovers all files and subdirectories
- [x] **Dynamic file discovery** - Parses HTML directory listings to discover files dynamically
- [x] **Handle file additions** - Automatically syncs newly added files from source
- [x] **Handle file deletions** - Compares S3 objects with source and deletes removed files

**Current Status:** ✅ **COMPLETE** - Full recursive directory traversal implemented with file discovery, sync, and deletion handling.

---

## Part 2: APIs

### ✅ Completed
- [x] Script to fetch data from DataUSA API
- [x] Save result as JSON file in S3
- [x] Error handling and retries
- [x] Timestamp-based naming

**Status:** ✅ **COMPLETE**

---

## Part 3: Data Analytics

### ✅ Completed
- [x] Load CSV file (`pr.data.0.Current`) as dataframe
- [x] Load JSON file from Part 2 as dataframe
- [x] Query 1: Mean and standard deviation of US population (2013-2018)
- [x] Query 2: Best year per series_id (year with max sum of values)
- [x] Query 3: Combined report (PRS30006032 Q01 + population)
- [x] Data cleaning (whitespace trimming)
- [x] Jupyter notebook (.ipynb) with all queries and results

**Status:** ✅ **COMPLETE**

---

## Part 4: Infrastructure as Code & Data Pipeline

### ✅ Completed
- [x] Using Terraform (IaC tool)
- [x] Lambda function that executes Part 1 & Part 2 (combined)
- [x] Lambda function scheduled to run daily (EventBridge)
- [x] SQS queue configured
- [x] S3 event notification to populate SQS when JSON file is written
- [x] Lambda function triggered by SQS that outputs Part 3 reports (logs results)

### ⚠️ Known Issues
- [ ] **Lambda package size** - Analytics Lambda exceeds 70MB (needs S3 upload or Lambda Layers)
- [ ] **S3 notification configuration** - Needs SQS policy fix (S3 service principal)

**Status:** ⚠️ **MOSTLY COMPLETE** (needs fixes for deployment)

---

## Summary

| Part | Status | Completion |
|------|--------|------------|
| Part 1 | ✅ Complete | 100% - Full recursive directory traversal implemented |
| Part 2 | ✅ Complete | 100% |
| Part 3 | ✅ Complete | 100% |
| Part 4 | ⚠️ Mostly Complete | ~90% - Infrastructure ready, needs deployment fixes |

### Remaining Issues

1. **Part 4: Deployment Fixes**
   - Fix Lambda package size issue (use S3 for large packages or Lambda Layers)
   - Fix S3 notification SQS policy (S3 service principal permissions)
   - Test end-to-end pipeline deployment

### Next Steps

1. ✅ ~~Implement full directory traversal for BLS sync~~ **DONE**
2. Fix Lambda package size issue (use S3 for large packages)
3. Fix S3 notification SQS policy
4. Test end-to-end pipeline

