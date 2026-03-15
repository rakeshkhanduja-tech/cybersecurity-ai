"""
aws_storage.py — Uploads connector CSV output to AWS S3.
Credentials are fetched from AWS Secrets Manager (cloud mode).
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone


class AwsS3Storage:
    def __init__(self, cfg: dict):
        self.bucket        = cfg.get("aws_s3_bucket", "evident-livedata")
        self.region        = cfg.get("aws_region", "us-east-1")
        self.secret_name   = cfg.get("aws_secret_name", "evident/s3-credentials")
        self.prefix        = cfg.get("aws_s3_prefix", "livedata")
        self._creds: dict | None = None

    def _get_creds(self) -> dict:
        if self._creds:
            return self._creds
        import boto3, json

        client = boto3.client("secretsmanager", region_name=self.region)
        secret = client.get_secret_value(SecretId=self.secret_name)
        self._creds = json.loads(secret["SecretString"])
        return self._creds

    def write(
        self,
        connector_id: str,
        api_id: str,
        schema: str,
        source_name: str,
        rows: list[dict],
    ) -> str:
        if not rows:
            return ""

        import boto3

        creds = self._get_creds()
        s3 = boto3.client(
            "s3",
            region_name=self.region,
            aws_access_key_id=creds.get("aws_access_key_id"),
            aws_secret_access_key=creds.get("aws_secret_access_key"),
        )

        now  = datetime.now(tz=timezone.utc)
        key  = f"{self.prefix}/{source_name}/{now.strftime('%m%d%Y')}/{now.strftime('%H')}/5M_{uuid.uuid4().hex[:12].upper()}.csv"

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

        s3.put_object(Bucket=self.bucket, Key=key, Body=buf.getvalue().encode("utf-8"))
        return f"s3://{self.bucket}/{key}"
