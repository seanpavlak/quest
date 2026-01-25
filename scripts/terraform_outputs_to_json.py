#!/usr/bin/env python3
"""Terraform output -> outputs.json. Used by CI, sync-outputs, refresh_outputs.sh."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def transform(raw: dict, *, environment: Optional[str] = None, region: str = "us-east-1") -> dict:
    values = {k: v["value"] for k, v in raw.items() if "value" in v}
    bucket_name = values.get("s3_bucket_name") or ""

    output: dict = {
        "s3_bucket_name": bucket_name,
        "s3_bucket_arn": values.get("s3_bucket_arn", ""),
        "s3_bucket_url": f"https://{bucket_name}.s3.{region}.amazonaws.com" if bucket_name else "",
        "s3_bucket_region": region,
        "data_sync_lambda_function_name": values.get("data_sync_lambda_function_name", ""),
        "data_sync_lambda_arn": values.get("data_sync_lambda_arn", ""),
        "analytics_lambda_function_name": values.get("analytics_lambda_function_name", ""),
        "analytics_lambda_arn": values.get("analytics_lambda_arn", ""),
        "sqs_queue_url": values.get("sqs_queue_url", ""),
        "sqs_queue_arn": values.get("sqs_queue_arn", ""),
        "cloudwatch_log_group_data_sync": values.get("cloudwatch_log_group_data_sync", ""),
        "cloudwatch_log_group_analytics": values.get("cloudwatch_log_group_analytics", ""),
        "terraform_state_bucket_name": values.get("terraform_state_bucket_name", ""),
        "terraform_state_bucket_arn": values.get("terraform_state_bucket_arn", ""),
        "terraform_state_lock_table_name": values.get("terraform_state_lock_table_name", ""),
        "terraform_state_lock_table_arn": values.get("terraform_state_lock_table_arn", ""),
    }

    if environment is not None:
        output["environment"] = environment

    if bucket_name:
        output["example_urls"] = {
            "bucket_root": f"https://{bucket_name}.s3.{region}.amazonaws.com/",
            "bls_main_file": f"https://{bucket_name}.s3.{region}.amazonaws.com/pr.data.0.Current",
            "population_data_pattern": f"https://{bucket_name}.s3.{region}.amazonaws.com/population_data_*.json",
        }

    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Transform Terraform JSON output into outputs.json")
    parser.add_argument("--input", "-i", help="Input JSON file (default: read from stdin)")
    parser.add_argument("--output", "-o", required=True, help="Output JSON file")
    parser.add_argument("--environment", "-e", choices=("dev", "prod"), help="Set 'environment' in output")
    parser.add_argument("--region", "-r", default="us-east-1", help="AWS region for URLs (default: us-east-1)")
    args = parser.parse_args()

    if args.input:
        path = Path(args.input)
        if not path.exists():
            print(f"Error: input file not found: {path}", file=sys.stderr)
            return 1
        data = json.loads(path.read_text())
    else:
        data = json.load(sys.stdin)

    out = transform(data, environment=args.environment, region=args.region)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(out, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
