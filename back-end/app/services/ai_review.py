import asyncio
import json
import re
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx
from fastapi import UploadFile

from app.core.config import settings
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
        if not settings.ai_api_base_url or not settings.ai_api_key:
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

        try:
            raw_result = await self.call_chat_completion(prompt, document_text)
        except Exception as exc:
            return AiPreReviewResult(
                passed=False,
                raw_result={"prompt": prompt, "document_text_preview": document_text[:1000]},
                issues=[
                    ReviewIssue(
                        type="AI_REVIEW_REQUEST_FAILED",
                        message=f"AI 初审请求失败（{type(exc).__name__}），请转人工审核。",
                    )
                ],
            )
        return self.parse_ai_result(raw_result)

    async def call_chat_completion(self, prompt: str, document_text: str) -> dict[str, Any]:
        base_url = settings.ai_api_base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        url = f"{base_url}/chat/completions"
        payload: dict[str, Any] = {
            "model": settings.ai_model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是场地申请材料初审助手。你只能返回一个 JSON 对象，"
                        "不要返回 Markdown，不要添加解释文字。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nWord 文本如下：\n{document_text}",
                },
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {settings.ai_api_key}"}

        async with httpx.AsyncClient(timeout=settings.ai_timeout_seconds) as client:
            for attempt in range(3):
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code == 400 and "response_format" in payload:
                    payload.pop("response_format", None)
                    response = await client.post(url, json=payload, headers=headers)
                if response.status_code not in {429, 500, 502, 503, 504} or attempt == 2:
                    response.raise_for_status()
                    return response.json()
                await asyncio.sleep(2**attempt)
        raise RuntimeError("AI request failed without a response")

    def parse_ai_result(self, raw_result: dict[str, Any]) -> AiPreReviewResult:
        try:
            content = raw_result["choices"][0]["message"]["content"]
            parsed = self.loads_json_object(content)
            normalized = self.normalize_result(parsed)
            normalized["raw_result"] = parsed
            return AiPreReviewResult.model_validate(normalized)
        except Exception as exc:
            return AiPreReviewResult(
                passed=False,
                raw_result=raw_result,
                issues=[
                    ReviewIssue(
                        type="AI_RESPONSE_PARSE_FAILED",
                        message=f"AI 初审结果解析失败：{exc}",
                    )
                ],
            )

    def loads_json_object(self, content: str) -> dict[str, Any]:
        content = content.strip()
        fence_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.S | re.I)
        if fence_match is not None:
            content = fence_match.group(1).strip()
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            unescaped_quotes = content.replace('\\\\"', '"').replace('\\"', '"')
            for candidate in (unescaped_quotes, content.encode().decode("unicode_escape")):
                if candidate == content:
                    continue
                try:
                    parsed = json.loads(candidate)
                except json.JSONDecodeError:
                    continue
                if isinstance(parsed, dict):
                    return parsed
            match = re.search(r"\{.*\}", content, flags=re.S)
            if match is None:
                raise
            parsed = json.loads(match.group(0))
        if not isinstance(parsed, dict):
            raise ValueError("AI response is not a JSON object")
        return parsed

    def normalize_result(self, parsed: dict[str, Any]) -> dict[str, Any]:
        issues = parsed.get("issues") or []
        normalized_issues = [
            {
                "type": str(issue.get("type") or "AI_REVIEW_ISSUE"),
                "message": str(issue.get("message") or issue),
            }
            if isinstance(issue, dict)
            else {"type": "AI_REVIEW_ISSUE", "message": str(issue)}
            for issue in issues
        ]

        time_slots = parsed.get("extracted_time_slots") or parsed.get("time_slots") or []
        normalized_slots = []
        for slot in time_slots:
            if not isinstance(slot, dict):
                continue
            date_value = str(slot.get("date") or "")
            start_time = str(slot.get("start_time") or "")
            end_time = str(slot.get("end_time") or "")
            normalized_slots.append(
                {
                    "date": date_value,
                    "start_time": start_time,
                    "end_time": end_time,
                    "start_at": self.combine_datetime(date_value, start_time),
                    "end_at": self.combine_datetime(date_value, end_time),
                }
            )

        return {
            "passed": bool(parsed.get("passed")) and not normalized_issues,
            "venue_name": parsed.get("venue_name"),
            "organization": parsed.get("organization"),
            "borrow_organization": parsed.get("borrow_organization") or parsed.get("organization"),
            "purpose_summary": parsed.get("purpose_summary") or parsed.get("activity_summary"),
            "applicant_name": parsed.get("applicant_name"),
            "extracted_time_slots": normalized_slots,
            "issues": normalized_issues,
        }

    def combine_datetime(self, date_value: str, time_value: str) -> datetime | None:
        if not date_value or not time_value:
            return None
        for fmt in ("%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(f"{date_value} {time_value}", fmt).replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            except ValueError:
                continue
        return None

    def build_prompt(self, application_type: str) -> str:
        if application_type == "auto":
            return self.build_prompt("meiyu_venue") + (
                "用户不再预选场地或日期，必须从文件中识别，不得猜测；场地名称缺失或涉及多个不同场地时，"
                "venue_name 返回 null 并在 issues 中说明。日期和时间均按中国标准时间（Asia/Shanghai）理解。"
                "若文件申请悦园三楼，应按活动策划书审核，并额外检查：首页是否包含精确到分钟的借用时间，"
                "一次申请最多 3 天且多天借用不得为连续自然日，正文活动安排与首页时间是否一致。"
                "未满足相应要求则 passed 返回 false 并说明原因。"
            )
        if application_type == "meiyu_venue":
            return (
                "你是山东大学美育场地申请初审助手。请从 Word 申请文件中提取申请房间、"
                "借用组织、申请人、场地用途简介、借用日期和具体时间段。"
                "借用组织是实际借用场地开展活动的组织、社团、学院或部门，不能简单使用当前登录用户所在部门替代。"
                "场地用途简介需要用 30-120 字概括本次借用用途，例如活动名称、活动性质、主要内容。"
                "如果没有明确个人申请人姓名，applicant_name 返回 null。只检查文件信息是否完整，"
                "不要判断数据库时间冲突，冲突由后端系统处理。请严格返回 JSON，格式为："
                "{\"passed\": true, \"venue_name\": \"\", \"organization\": \"\", "
                "\"borrow_organization\": \"\", "
                "\"purpose_summary\": \"\", \"applicant_name\": null, \"extracted_time_slots\": "
                "[{\"date\": \"YYYY-MM-DD\", \"start_time\": \"HH:mm\", "
                "\"end_time\": \"HH:mm\"}], \"issues\": []}。"
            )
        if application_type == "yueyuan_third_floor":
            return (
                "你是山东大学悦园三楼申请策划书初审助手。请检查首页是否包含精确到分钟的"
                "借用时间，例如 12:00-19:10；一次申请是否最多 3 天；多天借用是否不为"
                "连续自然日；正文活动安排时间是否与首页一致。不要判断数据库时间冲突，"
                "并请提取借用组织，借用组织是实际借用场地开展活动的组织、社团、学院或部门，"
                "不能简单使用当前登录用户所在部门替代。"
                "并请提取场地用途简介，用 30-120 字概括活动名称、活动性质、主要内容和借用用途。"
                "如果没有明确个人申请人姓名，applicant_name 返回 null。"
                "冲突由后端系统处理。请严格返回 JSON，格式为："
                "{\"passed\": true, \"venue_name\": \"悦园三楼\", \"organization\": \"\", "
                "\"borrow_organization\": \"\", "
                "\"purpose_summary\": \"\", \"applicant_name\": null, \"extracted_time_slots\": "
                "[{\"date\": \"YYYY-MM-DD\", \"start_time\": \"HH:mm\", "
                "\"end_time\": \"HH:mm\"}], \"issues\": []}。"
            )
        return (
            "请从申请文件中提取申请对象、借用组织、申请人、场地用途简介、借用日期和具体时间段。"
            "请严格返回 JSON。"
        )


ai_review_service = AiReviewService()
