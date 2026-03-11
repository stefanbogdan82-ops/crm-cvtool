from pathlib import Path
import re
import uuid

from cv_tool.app.core.config import settings


class LocalStorage:
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _sanitize_filename(self, filename: str) -> str:
        name = Path(filename).name
        name = re.sub(r'[<>:"/\\|?*]+', "_", name)
        name = re.sub(r"\s+", "_", name).strip("._")
        return name or "file"

    def save_bytes(
        self,
        data: bytes,
        subdir: str,
        filename: str,
        suffix: str | None = None,
    ) -> str:
        target_dir = self.base_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._sanitize_filename(filename)
        original_path = Path(safe_name)

        stem = original_path.stem
        ext = original_path.suffix

        final_name = f"{uuid.uuid4()}__{stem}"
        if suffix:
            final_name += f"__{suffix}"
        final_name += ext

        path = target_dir / final_name
        path.write_bytes(data)

        return str(path)


storage = LocalStorage(settings.storage_dir)