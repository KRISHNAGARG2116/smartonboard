import abc
import os
import uuid
import shutil
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from core.config import get_settings

settings = get_settings()


class StorageService(abc.ABC):
    @abc.abstractmethod
    def save_quarantine(self, content: bytes, filename: str) -> Path:
        """Saves a file in the quarantine directory under a secure random name. Returns the absolute Path."""
        pass

    @abc.abstractmethod
    def promote_file(self, quarantine_path: Path, tenant_id: str) -> Path:
        """Moves a verified file from quarantine to permanent storage under a secure random name. Returns the absolute Path."""
        pass

    @abc.abstractmethod
    def delete_file(self, path: Path) -> None:
        """Deletes a file securely from storage (quarantine or permanent)."""
        pass

    @abc.abstractmethod
    def get_signed_url(self, path: Path, expires_in_seconds: int = 3600) -> str:
        """Generates a secure temporary signed URL for file retrieval."""
        pass


class LocalStorageService(StorageService):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.quarantine_dir = self.base_dir / "quarantine"
        self.permanent_dir = self.base_dir / "uploads"
        
        # Ensure directories exist
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.permanent_dir.mkdir(parents=True, exist_ok=True)

    def save_quarantine(self, content: bytes, filename: str) -> Path:
        ext = Path(filename).suffix.lower()
        secure_name = f"{uuid.uuid4()}{ext}"
        target_path = self.quarantine_dir / secure_name
        
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o644
        fd = os.open(str(target_path), flags, mode)
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            
        return target_path

    def promote_file(self, quarantine_path: Path, tenant_id: str) -> Path:
        if not quarantine_path.exists():
            raise FileNotFoundError(f"Quarantine file not found: {quarantine_path}")
            
        tenant_dir = self.permanent_dir / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        
        ext = quarantine_path.suffix.lower()
        secure_name = f"{uuid.uuid4()}{ext}"
        target_path = tenant_dir / secure_name
        
        shutil.move(str(quarantine_path), str(target_path))
        target_path.chmod(0o644)
        return target_path

    def delete_file(self, path: Path) -> None:
        path_resolved = path.resolve()
        if not str(path_resolved).startswith(str(self.base_dir)):
            raise ValueError("Access Denied: Attempt to delete file outside storage base directory.")
            
        if path_resolved.exists():
            path_resolved.unlink()

    def get_signed_url(self, path: Path, expires_in_seconds: int = 3600) -> str:
        # Generates a temporary local path URL reference
        expiration = int(time.time()) + expires_in_seconds
        return f"http://localhost:8000/api/v1/files/download/{path.name}?token=mock_sig_{expiration}"


class S3StorageService(StorageService):
    """AWS S3 Cloud Storage implementation."""
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    def save_quarantine(self, content: bytes, filename: str) -> Path:
        return Path(f"/tmp/s3_quarantine/{uuid.uuid4()}_{filename}")

    def promote_file(self, quarantine_path: Path, tenant_id: str) -> Path:
        return Path(f"/s3_permanent/{tenant_id}/{quarantine_path.name}")

    def delete_file(self, path: Path) -> None:
        pass

    def get_signed_url(self, path: Path, expires_in_seconds: int = 3600) -> str:
        expiration = int(time.time()) + expires_in_seconds
        return f"https://{self.bucket_name}.s3.amazonaws.com/{path.name}?Signature=mock_s3_sig&Expires={expiration}"


class AzureBlobStorageService(StorageService):
    """Azure Blob Storage implementation."""
    def __init__(self, container_name: str):
        self.container_name = container_name

    def save_quarantine(self, content: bytes, filename: str) -> Path:
        return Path(f"/tmp/azure_quarantine/{uuid.uuid4()}_{filename}")

    def promote_file(self, quarantine_path: Path, tenant_id: str) -> Path:
        return Path(f"/azure_permanent/{tenant_id}/{quarantine_path.name}")

    def delete_file(self, path: Path) -> None:
        pass

    def get_signed_url(self, path: Path, expires_in_seconds: int = 3600) -> str:
        expiration = int(time.time()) + expires_in_seconds
        return f"https://mockaccount.blob.core.windows.net/{self.container_name}/{path.name}?se={expiration}&sig=mock_azure_sig"


class GCSStorageService(StorageService):
    """Google Cloud Storage implementation."""
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name

    def save_quarantine(self, content: bytes, filename: str) -> Path:
        return Path(f"/tmp/gcs_quarantine/{uuid.uuid4()}_{filename}")

    def promote_file(self, quarantine_path: Path, tenant_id: str) -> Path:
        return Path(f"/gcs_permanent/{tenant_id}/{quarantine_path.name}")

    def delete_file(self, path: Path) -> None:
        pass

    def get_signed_url(self, path: Path, expires_in_seconds: int = 3600) -> str:
        expiration = int(time.time()) + expires_in_seconds
        return f"https://storage.googleapis.com/{self.bucket_name}/{path.name}?GoogleAccessId=mock_gcs_id&Expires={expiration}"


# Storage Provider Factory
def get_storage_service() -> StorageService:
    provider = os.getenv("STORAGE_PROVIDER", "local").lower()
    
    if provider == "s3":
        return S3StorageService(bucket_name=os.getenv("S3_BUCKET_NAME", "smartonboard-uploads"))
    elif provider == "azure":
        return AzureBlobStorageService(container_name=os.getenv("AZURE_CONTAINER_NAME", "uploads"))
    elif provider == "gcs":
        return GCSStorageService(bucket_name=os.getenv("GCS_BUCKET_NAME", "smartonboard-uploads"))
    else:
        # Default local storage
        base_dir = Path(__file__).resolve().parent.parent / "data_storage"
        return LocalStorageService(base_dir=base_dir)


def enforce_storage_lifecycle_sweep(local_storage: LocalStorageService):
    """
    Enforces retention lifecycle checks:
    - Delete temporary files from quarantine older than 7 days.
    - Archive generated export reports older than 30 days.
    """
    now = datetime.now(timezone.utc)
    
    # 1. Clean quarantine directory (7 days TTL)
    if local_storage.quarantine_dir.exists():
        for file_path in local_storage.quarantine_dir.iterdir():
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
                if now - mtime > timedelta(days=7):
                    file_path.unlink()
                    
    # 2. Archive export reports (30 days TTL)
    reports_dir = local_storage.permanent_dir / "reports"
    if reports_dir.exists():
        for file_path in reports_dir.iterdir():
            if file_path.is_file():
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
                if now - mtime > timedelta(days=30):
                    # Mock archiving: move to archive subfolder or delete
                    archive_dir = local_storage.permanent_dir / "archive"
                    archive_dir.mkdir(exist_ok=True)
                    shutil.move(str(file_path), str(archive_dir / file_path.name))
