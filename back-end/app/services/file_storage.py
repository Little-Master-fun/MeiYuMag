from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import settings


class FileStorageService:
    async def save_upload(self, file: UploadFile, subdir: str) -> str:
        upload_root = Path(settings.upload_dir)
        target_dir = upload_root / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "").suffix.lower()
        stored_name = f"{uuid4().hex}{suffix}"
        stored_path = target_dir / stored_name

        await file.seek(0)
        content = await file.read()
        stored_path.write_bytes(content)
        await file.seek(0)
        return str(stored_path)


file_storage_service = FileStorageService()
