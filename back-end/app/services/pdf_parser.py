from io import BytesIO

from fastapi import HTTPException, UploadFile, status
from pypdf import PdfReader


class PdfParserService:
    async def extract_text(self, file: UploadFile) -> str:
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only .pdf files are supported for key borrowing applications",
            )

        content = await file.read()
        await file.seek(0)
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded PDF is empty")

        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not parse PDF") from exc

        parts = []
        for page in reader.pages:
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                parts.append(text)

        parsed_text = "\n".join(parts).strip()
        if not parsed_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未识别到 PDF 文字。请在扫描工具中开启文字识别（OCR），导出可搜索的 PDF 后重新上传；当前暂不支持普通照片或无文字层的纯图片 PDF。",
            )
        return parsed_text


pdf_parser_service = PdfParserService()
