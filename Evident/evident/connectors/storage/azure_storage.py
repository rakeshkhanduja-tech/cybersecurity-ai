"""
azure_storage.py — Uploads connector CSV output to Azure Data Lake Storage Gen2.
Credentials are fetched from Azure Key Vault (cloud mode).
"""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timezone


class AzureStorage:
    def __init__(self, cfg: dict):
        self.account_name  = cfg.get("azure_account_name", "")
        self.container     = cfg.get("azure_container", "evident-livedata")
        self.keyvault_url  = cfg.get("azure_keyvault_url", "")
        self.secret_name   = cfg.get("azure_secret_name", "adls-connection-string")
        self._conn_str: str | None = None

    def _get_connection_string(self) -> str:
        if self._conn_str:
            return self._conn_str

        if self.keyvault_url:
            # Fetch from Azure Key Vault using managed identity / env creds
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient
            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=self.keyvault_url, credential=credential)
            self._conn_str = client.get_secret(self.secret_name).value
        else:
            raise ValueError("azure_keyvault_url is required for Azure storage mode")

        return self._conn_str

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

        from azure.storage.filedatalake import DataLakeServiceClient

        conn_str = self._get_connection_string()
        service  = DataLakeServiceClient.from_connection_string(conn_str)
        fs       = service.get_file_system_client(self.container)

        now      = datetime.now(tz=timezone.utc)
        path     = f"{source_name}/{now.strftime('%m%d%Y')}/{now.strftime('%H')}/5M_{uuid.uuid4().hex[:12].upper()}.csv"

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        content = buf.getvalue().encode("utf-8")

        fc = fs.get_file_client(path)
        fc.create_file()
        fc.append_data(content, 0, len(content))
        fc.flush_data(len(content))

        return f"abfss://{self.container}@{self.account_name}.dfs.core.windows.net/{path}"
