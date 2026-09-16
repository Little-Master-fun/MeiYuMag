from pathlib import Path
from io import BytesIO
from urllib.parse import quote
from zipfile import ZipFile, ZIP_DEFLATED

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, Response

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
        "aliases": ["meiyu_signed_application_form"],
        "description": "现有申请表模板。签章阶段请填写、打印签字盖章后，上传清晰扫描件。",
    },
    "yueyuan_electricity_commitment": {
        "name": "用电安全承诺书.docx",
        "application_type": "yueyuan_third_floor",
        "file_type": "electricity_commitment_file",
        "filename": "yueyuan_electricity_commitment.docx",
        "aliases": ["electricity_commitment_signed_scan"],
        "description": "现有用电承诺书模板。扫描件须使用真实签字盖章后的文件。",
    },
    "yueyuan_safety_responsibility": {
        "name": "安全责任书（模板）.docx",
        "application_type": "yueyuan_third_floor",
        "file_type": "safety_responsibility_file",
        "filename": "yueyuan_safety_responsibility.docx",
        "aliases": ["safety_responsibility_signed_scan"],
        "description": "现有安全责任书模板。签章扫描件与填写后的原件分别上传。",
    },
    "yueyuan_safety_checklist": {
        "name": "山东大学大型会议（活动）安全工作排查清单.docx",
        "application_type": "yueyuan_third_floor",
        "file_type": "work_checklist_file",
        "filename": "yueyuan_safety_checklist.docx",
        "aliases": ["work_checklist_signed_scan"],
        "description": "现有安全排查清单模板。按实际活动逐项检查后填写。",
    },
    "meiyu_application_example": {
        "name": "填写示例.docx",
        "application_type": "meiyu_venue",
        "file_type": "pre_review_word",
        "filename": "meiyu_application_example.docx",
        "kind": "example",
        "description": "提供的活动申请填写参考，保留原文件内容与排版。请勿原样提交；正式申请请填写自己的活动信息。",
    },
    "yueyuan_plan_example": {
        "name": "悦园三楼活动策划书示例.docx",
        "application_type": "yueyuan_third_floor",
        "file_type": "yueyuan_plan_file",
        "aliases": ["pre_review_word", "yueyuan_plan_signed_scan"],
        "filename": "yueyuan_plan_example.docx",
        "kind": "example",
        "description": "非官方格式的内容示例。请按真实活动修改，签章阶段另附真实签章扫描件。",
    },
    "key_borrow_example": {
        "name": "美育钥匙借用示例.png",
        "application_type": "key_borrow",
        "file_type": "key_borrow_application",
        "filename": "key_borrow_example.png",
        "kind": "example",
        "description": "图片仅供填写参考，不是待提交材料。请填写自己的信息并签名；纸质材料请扫描，开启文字识别（OCR）并导出可搜索的 PDF。页面须完整、端正、清晰，不要直接上传普通拍照原图；当前暂不支持无文字层的纯图片 PDF。",
    },
    "supporting_material_example": {
        "name": "补充说明填写示例.docx",
        "application_type": "all",
        "file_type": "supporting_material",
        "filename": "supporting_material_example.docx",
        "kind": "example",
        "description": "通用补充说明示例，不替代申请表、正式证明或签章文件。",
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
            kind=template.get("kind", "template"),
            description=template.get("description", ""),
            aliases=template.get("aliases", []),
        )
        for template_id, template in APPLICATION_TEMPLATES.items()
    ]


@router.get("/bundles/yueyuan/download")
async def download_yueyuan_templates() -> Response:
    template_ids = (
        "yueyuan_electricity_commitment",
        "yueyuan_safety_responsibility",
        "yueyuan_safety_checklist",
    )
    archive = BytesIO()
    with ZipFile(archive, "w", compression=ZIP_DEFLATED) as bundle:
        for template_id in template_ids:
            template = APPLICATION_TEMPLATES[template_id]
            file_path = TEMPLATE_DIR / template["filename"]
            if not file_path.is_file():
                raise HTTPException(404, "Template file not found")
            bundle.write(file_path, arcname=template["name"])
    filename = quote("悦园三楼申请材料（三份模板）.zip")
    return Response(
        content=archive.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{filename}"},
    )


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
        media_type={
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }[file_path.suffix],
        filename=template["name"],
    )
