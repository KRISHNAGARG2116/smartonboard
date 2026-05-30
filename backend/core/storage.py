import abc
import os
import uuid
import shutil
from pathlib import Path

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


class LocalStorageService(StorageService):
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir.resolve()
        self.quarantine_dir = self.base_dir / "quarantine"
        self.permanent_dir = self.base_dir / "uploads"
        
        # Ensure directories exist
        self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        self.permanent_dir.mkdir(parents=True, exist_ok=True)

    def save_quarantine(self, content: bytes, filename: str) -> Path:
        # Generate random unique filename
        ext = Path(filename).suffix.lower()
        secure_name = f"{uuid.uuid4()}{ext}"
        target_path = self.quarantine_dir / secure_name
        
        # Write file with 0o644 permissions (read/write, no execute)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        mode = 0o644
        fd = os.open(str(target_path), flags, mode)
        with os.fdopen(fd, 'wb') as f:
            f.write(content)
            
        return target_path

    def promote_file(self, quarantine_path: Path, tenant_id: str) -> Path:
        if not quarantine_path.exists():
            raise FileNotFoundError(f"Quarantine file not found: {quarantine_path}")
            
        # Group permanent files by tenant to prevent collision and ensure clean RLS alignment
        tenant_dir = self.permanent_dir / str(tenant_id)
        tenant_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a new UUID to obscure any relationship
        ext = quarantine_path.suffix.lower()
        secure_name = f"{uuid.uuid4()}{ext}"
        target_path = tenant_dir / secure_name
        
        # Move the file securely
        shutil.move(str(quarantine_path), str(target_path))
        
        # Ensure permissions remain 0o644
        target_path.chmod(0o644)
        
        return target_path

    def delete_file(self, path: Path) -> None:
        # Security check: Ensure we only delete within base_dir to prevent path traversal
        path_resolved = path.resolve()
        if not str(path_resolved).startswith(str(self.base_dir)):
            raise ValueError("Access Denied: Attempt to delete file outside storage base directory.")
            
        if path_resolved.exists():
            path_resolved.unlink()
