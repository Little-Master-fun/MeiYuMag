from pathlib import Path
from uuid import uuid4
import zipfile

from fastapi import UploadFile, HTTPException

from app.core.config import settings


class FileStorageService:
    async def validate_upload(self, file: UploadFile) -> int:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".doc", ".docx", ".pdf", ".png", ".jpg", ".jpeg"}:
            raise HTTPException(400, "仅支持 Word、PDF 和 PNG/JPEG 图片")
        size = 0
        await file.seek(0)
        head = await file.read(16)
        size += len(head)
        try:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_size_mb * 1024 * 1024:
                    raise HTTPException(413, f"单份文件不能超过 {settings.max_upload_size_mb}MB")
            signatures = {".pdf": b"%PDF-", ".png": b"\x89PNG\r\n\x1a\n", ".jpg": b"\xff\xd8\xff",
                          ".jpeg": b"\xff\xd8\xff", ".doc": b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", ".docx": b"PK"}
            if not size or not head.startswith(signatures[suffix]):
                raise HTTPException(400, "文件内容与扩展名不符，或文件为空")
            if suffix == ".docx":
                try:
                    with zipfile.ZipFile(file.file) as archive:
                        names = archive.namelist()
                        if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                            raise ValueError()
                        if any("vbaproject" in n.lower() for n in names):
                            raise ValueError()
                        if sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
                            raise ValueError()
                except (zipfile.BadZipFile, ValueError):
                    raise HTTPException(400, "Word 文档损坏、包含宏或解压后过大")
            return size
        finally:
            await file.seek(0)

    async def validate_batch(self, files: list[UploadFile]) -> None:
        if not files or len(files) > 10:
            raise HTTPException(400, "每次提交 1 至 10 份文件")
        total = 0
        for file in files:
            total += await self.validate_upload(file)
        if total > 100 * 1024 * 1024:
            raise HTTPException(413, "本次材料总大小不能超过 100MB")

    async def save_upload(self, file: UploadFile, subdir: str) -> str:
        await self.validate_upload(file)
        upload_root = Path(settings.upload_dir)
        target_dir = upload_root / subdir
        target_dir.mkdir(parents=True, exist_ok=True)

        suffix = Path(file.filename or "").suffix.lower()
        stored_name = f"{uuid4().hex}{suffix}"
        stored_path = target_dir / stored_name

        await file.seek(0)
        try:
            with stored_path.open("wb") as target:
                while chunk := await file.read(1024 * 1024):
                    target.write(chunk)
        except BaseException:
            stored_path.unlink(missing_ok=True)
            raise
        await file.seek(0)
        return str(stored_path)


file_storage_service = FileStorageService()
