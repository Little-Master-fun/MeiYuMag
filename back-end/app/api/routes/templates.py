from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.schemas.template import ApplicationTemplateRead

router = APIRouter(prefix="/templates", tags=["templates"])

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "static" / "templates"

APPLICATION_TEMPLATES = {
    "meiyu_activity_application": {
        "name": "山东大学美育文化馆活动申请表.docx",
        "application_type": "meiyu_venue",
        "file_type": "meiyu_application_form",
        "filename": "meiyu_activity_application.docx",
    },
    "yueyuan_electricity_commitment": {
        "name": "用电安全承诺书.docx",
        "application_type": "yueyuan_third_floor",
        "file_type": "electricity_commitment_file",
        "filename": "yueyuan_electricity_commitment.docx",
    },
    "yueyuan_safety_responsibility": {
        "name": "安全责任书（模板）.docx",
        "application_type": "yueyuan_third_floor",
        "file_type": "safety_responsibility_file",
        "filename": "yueyuan_safety_responsibility.docx",
    },
    "yueyuan_safety_checklist": {
        "name": "山东大学大型会议（活动）安全工作排查清单.docx",
        "application_type": "yueyuan_third_floor",
        "file_type": "work_checklist_file",
        "filename": "yueyuan_safety_checklist.docx",
    },
}


@router.get("", response_model=list[ApplicationTemplateRead])
async def list_application_templates() -> list[ApplicationTemplateRead]:
    return [
        ApplicationTemplateRead(
            id=template_id,
            name=template["name"],
            application_type=template["application_type"],
            file_type=template["file_type"],
            download_url=f"{settings.api_v1_prefix}/templates/{template_id}/download",
        )
        for template_id, template in APPLICATION_TEMPLATES.items()
    ]


@router.get("/{template_id}/download")
async def download_application_template(template_id: str) -> FileResponse:
    template = APPLICATION_TEMPLATES.get(template_id)
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    file_path = TEMPLATE_DIR / template["filename"]
    if not file_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template file not found")

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=template["name"],
    )
