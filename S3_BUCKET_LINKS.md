# S3 Bucket Links - For Submission

## Bucket Information

**Bucket Name:** `rearc-data-pipeline-data-8299e21f`  
**Region:** `us-east-1`  
**Public Access:** ✅ Enabled (read-only)

## Public URLs

### Main Bucket URL
```
https://rearc-data-pipeline-data-8299e21f.s3.amazonaws.com/
```

### BLS Data File (Part 1)
```
https://rearc-data-pipeline-data-8299e21f.s3.amazonaws.com/pr.data.0.Current
```

### Population Data Files (Part 2)
```
https://rearc-data-pipeline-data-8299e21f.s3.amazonaws.com/population_data_20260111_204633.json
```

## Verification

You can verify access by:
1. Opening the URLs in a browser
2. Or using curl:
   ```bash
   curl https://rearc-data-pipeline-data-8299e21f.s3.amazonaws.com/pr.data.0.Current
   ```

## Files in Bucket

- `pr.data.0.Current` - BLS time-series data (1.5MB)
- `population_data_*.json` - Population data from DataUSA API

## Note

The bucket is configured with:
- ✅ Public read access (for sharing)
- ✅ Versioning enabled
- ✅ Server-side encryption (AES256)
- ✅ All BLS files synced via recursive directory traversal

