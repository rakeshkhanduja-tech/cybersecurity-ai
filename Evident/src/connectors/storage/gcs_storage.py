"""
gcs_storage.py — Uploads connector CSV output to Google Cloud Storage.
Credentials are fetched from GCP Secret Manager (cloud mode).
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone


class GcsStorage:
    def __init__(self, cfg: dict):
        self.bucket      = cfg.get("gcs_bucket", "evident-livedata")
        self.project     = cfg.get("gcp_project", "")
        self.secret_name = cfg.get("gcp_secret_name", "evident-gcs-key")
        self.prefix      = cfg.get("gcs_prefix", "livedata")
        self._sa_info: dict | None = None

    def _get_service_account(self) -> dict:
        if self._sa_info:
            return self._sa_info
        import json
        from google.cloud import secretmanager

        client   = secretmanager.SecretManagerServiceClient()
        resource = f"projects/{self.project}/secrets/{self.secret_name}/versions/latest"
        response = client.access_secret_version(name=resource)
        self._sa_info = json.loads(response.payload.data.decode("utf-8"))
        return self._sa_info

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

        from google.cloud import storage as gcs
        from google.oauth2 import service_account

        sa_info = self._get_service_account()
        creds   = service_account.Credentials.from_service_account_info(sa_info)
        client  = gcs.Client(project=self.project, credentials=creds)
        bucket  = client.bucket(self.bucket)

        now     = datetime.now(tz=timezone.utc)
        blob_name = f"{self.prefix}/{source_name}/{now.strftime('%m%d%Y')}/{now.strftime('%H')}/5M_{uuid.uuid4().hex[:12].upper()}.csv"

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

        blob = bucket.blob(blob_name)
        blob.upload_from_string(buf.getvalue(), content_type="text/csv")

        return f"gs://{self.bucket}/{blob_name}"
