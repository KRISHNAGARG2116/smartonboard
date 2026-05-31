import abc
from pathlib import Path
import uuid
from sqlalchemy import select, text
from sqlalchemy.orm import Session

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


def archive_old_audit_logs(
    db: Session,
    company_id: uuid.UUID | None,
    provider: ArchiveStorageProvider,
    days: int = 90
) -> str | None:
    """Archive logs older than X days to cold storage, then purge from hot SQL database under secure bypass context."""
    from datetime import datetime, timedelta, timezone
    import json
    import uuid as py_uuid
    from models.audit import AuditLog
    from db.session import tenant_context
    
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Query logs to archive under auth_mode="true" (system-level RLS bypass)
    with tenant_context(auth_mode="true"):
        stmt = select(AuditLog).where(AuditLog.timestamp < cutoff)
        if company_id:
            stmt = stmt.where(AuditLog.company_id == company_id)
            
        old_logs = db.scalars(stmt).all()
        if not old_logs:
            return None
            
        # Serialize logs to JSON bytes
        log_data = []
        for log in old_logs:
            log_data.append({
                "id": str(log.id),
                "company_id": str(log.company_id) if log.company_id else None,
                "actor_id": str(log.actor_id) if log.actor_id else None,
                "actor_type": log.actor_type,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "metadata_json": log.metadata_json,
                "timestamp": log.timestamp.isoformat()
            })
            
        archive_content = json.dumps(log_data).encode("utf-8")
        
        # Save archive using the provider
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        comp_prefix = str(company_id) if company_id else "global"
        filename = f"audit_archive_{comp_prefix}_{timestamp_str}.json"
        archive_uri = provider.upload_archive(filename, archive_content)
        
        # Purge archived records from database under secure bypass context
        db.execute(text("SELECT set_config('app.bypass_audit_immutability', 'true', true)"))
        for log in old_logs:
            db.delete(log)
        db.commit()
        db.execute(text("SELECT set_config('app.bypass_audit_immutability', 'false', true)"))
        
        return archive_uri
