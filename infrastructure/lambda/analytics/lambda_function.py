"""Analytics Lambda: process SQS/S3 events, run queries."""

import json
import logging
import os
from io import StringIO
from typing import Any, Dict, List, Optional

import boto3
import pandas as pd
from botocore.exceptions import ClientError, BotoCoreError

from rearc.analytics import (
    query1_population_stats,
    query2_best_year_per_series,
    query3_combined_report
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

POPULATION_FILE_PREFIX = "population_data_"
POPULATION_FILE_SUFFIX = ".json"
DEFAULT_BLS_FILE_KEY = "pr.data.0.Current"

s3_client = boto3.client('s3')


def load_data_from_s3(bucket_name: str, key: str) -> str:
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=key)
        return response['Body'].read().decode('utf-8')
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Error loading {key} from S3: {e}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    bls_file_key = os.environ.get('BLS_FILE_KEY', DEFAULT_BLS_FILE_KEY)
    
    if not bucket_name:
        logger.error("S3_BUCKET_NAME environment variable not set")
        raise RuntimeError("S3_BUCKET_NAME not configured")
    
    results: Dict[str, Any] = {}
    records: List[Dict[str, Any]] = event.get('Records', [])
    
    if not records:
        logger.warning("No records found in event")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No records to process'})
        }
    for record in records:
        try:
            body = json.loads(record['body'])
            if 'Message' in body:
                s3_event = json.loads(body['Message'])
                s3_records = s3_event.get('Records', [])
            elif 'Records' in body:
                s3_records = body.get('Records', [])
            else:
                logger.warning(f"Unexpected message format: {list(body.keys())}")
                continue
            for s3_record in s3_records:
                s3_object = s3_record['s3']
                object_key = s3_object['object']['key']
                object_bucket = s3_object['bucket']['name']
                
                logger.info(f"Processing S3 object: s3://{object_bucket}/{object_key}")
                if (object_key.startswith(POPULATION_FILE_PREFIX) and
                        object_key.endswith(POPULATION_FILE_SUFFIX)):
                    population_content = load_data_from_s3(object_bucket, object_key)
                    population_data = json.loads(population_content)
                    population_df = pd.DataFrame(population_data.get('data', []))
                    bls_content = load_data_from_s3(object_bucket, bls_file_key)
                    bls_df = pd.read_csv(StringIO(bls_content), sep='\t')
                    string_columns = bls_df.select_dtypes(include=['object']).columns
                    for col in string_columns:
                        bls_df[col] = bls_df[col].str.strip()
                    results['query1'] = query1_population_stats(population_df)
                    results['query2'] = query2_best_year_per_series(bls_df).to_dict('records')
                    results['query3'] = query3_combined_report(bls_df, population_df).to_dict('records')
                    logger.info(f"Query 1 Results: {results['query1']}")
                    logger.info(f"Query 2 Results: {len(results['query2'])} records")
                    logger.info(f"Query 3 Results: {len(results['query3'])} records")
                    
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Error parsing record: {str(e)}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error processing record: {str(e)}", exc_info=True)
            raise

    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

