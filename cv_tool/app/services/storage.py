import os
import uuid
from pathlib import Path
from app.core.config import settings

class LocalStorage:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, data: bytes, subdir: str, filename: str) -> str:
        d = self.base_dir / subdir
        d.mkdir(parents=True, exist_ok=True)
        safe_name = filename.replace("/", "_").replace("\\", "_")
        path = d / f"{uuid.uuid4()}__{safe_name}"
        path.write_bytes(data)
        return str(path)

storage = LocalStorage(settings.storage_dir)
