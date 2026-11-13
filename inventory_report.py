"""Export an S3 object inventory as CSV without downloading object contents."""

import csv


def write_inventory(client, bucket, prefix, output):
    """Stream paginated object metadata and return object/byte totals."""
    writer = csv.DictWriter(output, fieldnames=[
        "bucket", "key", "size_bytes", "last_modified", "storage_class"
    ])
    writer.writeheader()
    totals = {"objects": 0, "bytes": 0}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            modified = obj.get("LastModified", "")
            writer.writerow({
                "bucket": bucket, "key": obj["Key"], "size_bytes": obj["Size"],
                "last_modified": modified.isoformat() if hasattr(modified, "isoformat") else modified,
                "storage_class": obj.get("StorageClass", "STANDARD"),
            })
            totals["objects"] += 1
            totals["bytes"] += obj["Size"]
    return totals


class SnapshotClient:
    """Read a saved ListObjectsV2 response for repeatable offline reports."""

    def __init__(self, response):
        self.response = response

    def get_paginator(self, name):
        return self

    def paginate(self, **kwargs):
        yield self.response


def load_settings(path):
    import tomllib

    with open(path, "rb") as source:
        return tomllib.load(source)


def create_client(settings):
    import boto3
    from botocore.config import Config

    aws = settings.get("aws", {})
    access_key = aws.get("aws_access_key_id", "").strip()
    secret_key = aws.get("aws_secret_access_key", "").strip()
    if not access_key or not secret_key:
        raise ValueError("Set aws_access_key_id and aws_secret_access_key in the settings file")
    return boto3.client(
        "s3", region_name=aws.get("region", "us-east-1"),
        aws_access_key_id=access_key, aws_secret_access_key=secret_key,
        config=Config(connect_timeout=5, read_timeout=30,
                      retries={"mode": "standard", "total_max_attempts": 3}),
    )


def main(argv=None):
    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).parent / "config/settings.toml")
    parser.add_argument("--bucket", help="Override the configured bucket")
    parser.add_argument("--prefix", help="Override the configured key prefix")
    parser.add_argument("--snapshot", type=Path, help="Read a saved S3 response instead of contacting AWS")
    parser.add_argument("--output", type=Path, default=Path("reports/inventory.csv"))
    args = parser.parse_args(argv)
    settings = {} if args.snapshot else load_settings(args.config)
    report = settings.get("report", {})
    bucket = args.bucket or report.get("bucket")
    prefix = args.prefix if args.prefix is not None else report.get("prefix", "")
    if not bucket:
        parser.error("Set report.bucket in settings or supply --bucket")
    client = (SnapshotClient(json.loads(args.snapshot.read_text()))
              if args.snapshot else create_client(settings))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as output:
        stats = write_inventory(client, bucket, prefix, output)
    print(f"Wrote {stats['objects']} objects ({stats['bytes']} bytes) to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
