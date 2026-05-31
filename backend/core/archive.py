import abc
from pathlib import Path

class ArchiveStorageProvider(abc.ABC):
    """Abstract base class for cold-storage audit log archives, decoupling cloud provider specifics."""

    @abc.abstractmethod
    def upload_archive(self, filename: str, content: bytes) -> str:
        """Upload cold archive contents and return the saved path/URI string."""
        pass

    @abc.abstractmethod
    def download_archive(self, filename: str) -> bytes:
        """Download and return the raw bytes of an archived file."""
        pass


class LocalArchiveProvider(ArchiveStorageProvider):
    """Development/testing archive provider utilizing local file storage."""

    def __init__(self, base_dir: str = "storage/archive"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def upload_archive(self, filename: str, content: bytes) -> str:
        dest_path = self.base_dir / filename
        dest_path.write_bytes(content)
        # Set restricted read/write permissions
        dest_path.chmod(0o600)
        return str(dest_path.resolve())

    def download_archive(self, filename: str) -> bytes:
        src_path = self.base_dir / filename
        if not src_path.exists():
            raise FileNotFoundError(f"Archive file '{filename}' not found.")
        return src_path.read_bytes()


class S3ArchiveProvider(ArchiveStorageProvider):
    """Production archive provider leveraging S3-compatible endpoints (AWS, MinIO, GCS via S3 API)."""

    def __init__(self, bucket_name: str = "smartonboard-compliance-archives"):
        self.bucket_name = bucket_name

    def upload_archive(self, filename: str, content: bytes) -> str:
        # Stub implementation ready for future boto3/minio client bindings
        uri = f"s3://{self.bucket_name}/{filename}"
        print(f"S3_ARCHIVE: Uploaded {len(content)} bytes to {uri} (stubbed)")
        return uri

    def download_archive(self, filename: str) -> bytes:
        # Stub implementation returning mock bytes
        print(f"S3_ARCHIVE: Downloading {filename} from s3://{self.bucket_name} (stubbed)")
        return b"{}"
