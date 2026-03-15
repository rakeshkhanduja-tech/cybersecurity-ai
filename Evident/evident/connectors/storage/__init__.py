"""
storage/__init__.py — Factory that returns the correct storage backend
based on the storage_type config field.
"""
from __future__ import annotations


def get_storage(storage_cfg: dict):
    """
    storage_cfg keys:
      storage_type : 'local' | 'azure' | 'aws_s3' | 'gcs'
      ... backend-specific keys ...
    """
    stype = storage_cfg.get("storage_type", "local").lower()

    if stype == "azure":
        from evident.connectors.storage.azure_storage import AzureStorage
        return AzureStorage(storage_cfg)
    if stype == "aws_s3":
        from evident.connectors.storage.aws_storage import AwsS3Storage
        return AwsS3Storage(storage_cfg)
    if stype == "gcs":
        from evident.connectors.storage.gcs_storage import GcsStorage
        return GcsStorage(storage_cfg)

    from evident.connectors.storage.local_storage import LocalStorage
    return LocalStorage(storage_cfg)
