from datetime import datetime
from typing import Any

from fastapi import UploadFile

from app.core.config import settings
from app.schemas.key import KeyBorrowAiResult
from app.services.ai_review import ai_review_service
from app.services.pdf_parser import pdf_parser_service


class KeyAiReviewService:
    async def extract_key_borrow_info(self, file: UploadFile) -> KeyBorrowAiResult:
        document_text = await pdf_parser_service.extract_text(file)
        if not settings.ai_api_base_url or not settings.ai_api_key:
            return KeyBorrowAiResult(
                issues=["AI review is not configured. PDF text extraction succeeded."],
                raw_result={"document_text_preview": document_text[:1000]},
            )

        prompt = (
            "你是山东大学钥匙借用申请信息提取助手。请从 PDF 申请文本中提取："
            "1. 借用组织；2. 借用的钥匙名称或房间名称；3. 借用开始时间；4. 预计归还时间。"
            "借用组织是实际借用钥匙的组织、社团、学院或部门。"
            "如果只有借用日期和时间段，请组合成完整时间。"
            "请严格返回 JSON，格式为："
            "{\"borrow_organization\": \"\", \"borrowed_key_name\": \"\", "
            "\"borrowed_at\": \"YYYY-MM-DDTHH:mm:ss\", "
            "\"expected_return_at\": \"YYYY-MM-DDTHH:mm:ss\", \"issues\": []}。"
        )
        try:
            raw_result = await ai_review_service.call_chat_completion(prompt, document_text)
        except Exception as exc:
            return KeyBorrowAiResult(
                issues=[f"AI key borrowing extraction failed: {exc}"],
                raw_result={"document_text_preview": document_text[:1000]},
            )
        return self.parse_result(raw_result)

    def parse_result(self, raw_result: dict[str, Any]) -> KeyBorrowAiResult:
        try:
            content = raw_result["choices"][0]["message"]["content"]
            parsed = ai_review_service.loads_json_object(content)
            return KeyBorrowAiResult(
                borrowed_key_name=parsed.get("borrowed_key_name") or parsed.get("key_name"),
                borrow_organization=parsed.get("borrow_organization") or parsed.get("organization"),
                borrowed_at=self.parse_datetime(parsed.get("borrowed_at")),
                expected_return_at=self.parse_datetime(parsed.get("expected_return_at")),
                issues=[str(issue) for issue in (parsed.get("issues") or [])],
                raw_result=parsed,
            )
        except Exception as exc:
            return KeyBorrowAiResult(
                issues=[f"AI key borrowing response parse failed: {exc}"],
                raw_result=raw_result,
            )

    def parse_datetime(self, value: object) -> datetime | None:
        if not value:
            return None
        text = str(value).strip()
        for parser in (datetime.fromisoformat,):
            try:
                return parser(text)
            except ValueError:
                continue
        for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None


key_ai_review_service = KeyAiReviewService()
