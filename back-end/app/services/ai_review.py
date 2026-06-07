from fastapi import UploadFile

from app.schemas.application import AiPreReviewResult, ReviewIssue
from app.services.word_parser import word_parser_service


class AiReviewService:
    async def pre_review_word(
        self,
        application_type: str,
        file: UploadFile,
    ) -> AiPreReviewResult:
        prompt = self.build_prompt(application_type)
        document_text = await word_parser_service.extract_text(file)
        # TODO: call the configured AI provider with prompt and document_text.
        # The AI should return structured JSON matching AiPreReviewResult.
        return AiPreReviewResult(
            passed=False,
            raw_result={"prompt": prompt, "document_text_preview": document_text[:1000]},
            issues=[
                ReviewIssue(
                    type="AI_REVIEW_NOT_CONFIGURED",
                    message="AI pre-review is not configured yet. Word text extraction succeeded.",
                )
            ],
        )

    def build_prompt(self, application_type: str) -> str:
        if application_type == "meiyu_venue":
            return (
                "你是山东大学美育场地申请初审助手。请从 Word 申请文件中提取申请房间、"
                "申请组织、申请人、借用日期和具体时间段。只检查文件信息是否完整，"
                "不要判断数据库时间冲突，冲突由后端系统处理。请返回 JSON。"
            )
        if application_type == "yueyuan_third_floor":
            return (
                "你是山东大学悦园三楼申请策划书初审助手。请检查首页是否包含精确到分钟的"
                "借用时间，例如 12:00-19:10；一次申请是否最多 3 天；多天借用是否不为"
                "连续自然日；正文活动安排时间是否与首页一致。不要判断数据库时间冲突，"
                "冲突由后端系统处理。请返回 JSON。"
            )
        return (
            "请从申请文件中提取申请对象、申请组织、申请人、借用日期和具体时间段。"
            "请返回 JSON。"
        )


ai_review_service = AiReviewService()
