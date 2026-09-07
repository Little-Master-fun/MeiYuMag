"""Isolated HTTP workflow tests: no real database, AI service or email is used.

Run: python -m unittest discover -s tests -v
"""
import tempfile
import unittest
from datetime import datetime, timezone
from io import BytesIO
from unittest.mock import AsyncMock, patch

import httpx
from docx import Document
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.main import create_app
from app.db.base import Base
from app.db.session import get_db
from app.core.config import settings
from app.core.security import create_access_token
from app.models import Application, ApplicationFile, ReservationCalendar, User, Venue
from app.schemas.application import AiPreReviewResult, ExtractedTimeSlot, ReviewIssue
from app.services.application_workflow import signed_file_types


def word_bytes():
    buffer = BytesIO()
    doc = Document()
    doc.add_paragraph("会议室申请，2035-12-20，09:00—11:00，测试组织")
    doc.save(buffer)
    return buffer.getvalue()


class WorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as db:
            db.add_all([User(id=1, email="user@test.invalid", password_hash="unused", role="user", is_application_allowed=True),
                        User(id=2, email="admin@test.invalid", password_hash="unused", role="admin"),
                        User(id=3, email="other@test.invalid", password_hash="unused", role="user"),
                        Venue(id=1, name="会议室", venue_type="meiyu"), Venue(id=2, name="悦园三楼", venue_type="yueyuan")])
            await db.commit()
        self.app = create_app()
        async def database():
            async with self.sessions() as db:
                yield db
        self.app.dependency_overrides[get_db] = database
        self.temp = tempfile.TemporaryDirectory(prefix="meiyu-workflow-test-")
        self.patches = [patch.object(settings, "upload_dir", self.temp.name),
                        patch("app.api.routes.applications.ai_review_service.pre_review_word", new_callable=AsyncMock),
                        patch("app.services.notification.notification_service.send_and_log", new_callable=AsyncMock),
                        patch("app.services.notification.notification_service.notify_admins", new_callable=AsyncMock),
                        patch("app.api.routes.admin.email_service.send_text_email", return_value="skipped")]
        started = [p.start() for p in self.patches]
        self.ai = started[1]
        self.ai.return_value = AiPreReviewResult(passed=True, venue_name="会议室", borrow_organization="测试组织", extracted_time_slots=[
            ExtractedTimeSlot(date="2035-12-20", start_time="09:00", end_time="11:00",
                              start_at=datetime(2035,12,20,1,tzinfo=timezone.utc), end_at=datetime(2035,12,20,3,tzinfo=timezone.utc))])
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app), base_url="http://test", headers=self.headers(1))

    async def asyncTearDown(self):
        await self.client.aclose()
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()
        await self.engine.dispose()

    def headers(self, user_id):
        return {"Authorization": f"Bearer {create_access_token(str(user_id))}"}

    async def initial(self, venue=1):
        return await self.client.post("/api/v1/applications/pre-review", data={"application_type": "meiyu_venue" if venue == 1 else "yueyuan_third_floor", "venue_id": str(venue), "expected_date": "2035-12-20"}, files={"file": ("application.docx", word_bytes())})

    async def signed(self, application_id, types=None):
        return await self.client.post(f"/api/v1/applications/{application_id}/signed-files", files=[(key, ("signed.pdf", b"%PDF-1.7 test")) for key in (types or ["meiyu_signed_application_form"])])

    async def request_supplement(self, application_id, types):
        return await self.client.post(f"/api/v1/admin/applications/{application_id}/request-supplement", headers=self.headers(2), json={"file_types": types, "reason": "签章不清晰，请重新扫描"})

    async def test_full_reject_retry_signed_supplement_complete(self):
        self.ai.return_value.passed = False
        self.ai.return_value.issues = [ReviewIssue(type="MISSING_SIGNATURE", message="缺少申请信息")]
        response = await self.initial(); self.assertEqual(response.status_code, 200, response.text)
        app_id = response.json()["application_id"]
        self.assertEqual(response.json()["next_status"], "ai_rejected")
        detail = (await self.client.get(f"/api/v1/applications/{app_id}")).json()
        self.assertIn("缺少申请信息", detail["review_reason"])
        self.ai.return_value.passed = True; self.ai.return_value.issues = []
        retry = await self.client.post(f"/api/v1/applications/{app_id}/pre-review", files={"file": ("retry.docx", word_bytes())})
        self.assertEqual(retry.json()["next_status"], "pending_signed_files")
        self.assertEqual((await self.signed(app_id)).json()["status"], "pending_admin_submit")
        required = ["meiyu_signed_application_form", "supporting_material"]
        self.assertEqual((await self.request_supplement(app_id, required)).status_code, 200)
        detail = (await self.client.get(f"/api/v1/applications/{app_id}")).json()
        self.assertEqual(detail["requested_file_types"], required)
        self.assertEqual(detail["review_reason"], "签章不清晰，请重新扫描")
        uploaded = await self.client.post(f"/api/v1/applications/{app_id}/files/batch", files=[
            ("file_types", (None, required[0])), ("files", ("signed-new.pdf", b"%PDF-1.7 new")),
            ("file_types", (None, required[1])), ("files", ("explanation.pdf", b"%PDF-1.7 explanation"))])
        self.assertEqual(uploaded.status_code, 200, uploaded.text)
        files = (await self.client.get(f"/api/v1/applications/{app_id}/files")).json()
        signed_files = [f for f in files if f["file_type"] == required[0]]
        self.assertEqual([f["version"] for f in signed_files], [2,1])
        self.assertEqual(signed_files[0]["review_status"], "pending_admin_review")
        self.assertEqual(signed_files[1]["review_status"], "rejected")
        for state in ("submitted", "completed"):
            response = await self.client.patch(f"/api/v1/admin/applications/{app_id}/status", headers=self.headers(2), json={"status": state})
            self.assertEqual(response.status_code, 200, response.text)
        async with self.sessions() as db:
            reservations = (await db.execute(select(ReservationCalendar))).scalars().all()
            self.assertEqual([r.status for r in reservations], ["confirmed"])

    async def test_missing_or_duplicate_supplements_do_not_advance(self):
        app_id = (await self.initial()).json()["application_id"]
        await self.signed(app_id)
        await self.request_supplement(app_id, ["meiyu_signed_application_form", "supporting_material"])
        for types in (["supplement_file"], ["meiyu_signed_application_form"], ["meiyu_signed_application_form"] * 2):
            payload = []
            for kind in types:
                payload.extend([("file_types", (None, kind)), ("files", ("new.pdf", b"%PDF-1.7"))])
            result = await self.client.post(f"/api/v1/applications/{app_id}/files/batch", files=payload)
            self.assertEqual(result.status_code, 400, result.text)
        result = await self.signed(app_id)
        self.assertEqual(result.status_code, 400)
        detail = (await self.client.get(f"/api/v1/applications/{app_id}")).json()
        self.assertEqual(detail["status"], "supplement_required")

    async def test_yueyuan_requires_all_eight_signed_files(self):
        self.ai.return_value.venue_name = "悦园三楼"
        app_id = (await self.initial(2)).json()["application_id"]
        types = signed_file_types("yueyuan_third_floor")
        self.assertEqual(len(types), 8)
        self.assertEqual((await self.signed(app_id, types[:7])).status_code, 400)
        response = await self.signed(app_id, types)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["uploaded_files"]), 8)

    async def test_permissions_and_invalid_admin_transitions(self):
        app_id = (await self.initial()).json()["application_id"]
        self.assertEqual((await self.client.get("/api/v1/admin/applications")).status_code, 403)
        for path in (f"/api/v1/applications/{app_id}", f"/api/v1/applications/{app_id}/files"):
            self.assertEqual((await self.client.get(path, headers=self.headers(3))).status_code, 403)
        result = await self.client.patch(f"/api/v1/admin/applications/{app_id}/status", headers=self.headers(2), json={"status": "completed"})
        self.assertEqual(result.status_code, 409)
        await self.signed(app_id)
        self.assertEqual((await self.request_supplement(app_id, ["made_up_type"])).status_code, 400)
        result = await self.client.patch(f"/api/v1/admin/applications/{app_id}/status", headers=self.headers(2), json={"status": "rejected"})
        self.assertEqual(result.status_code, 400)

    async def test_upload_validation_before_ai_and_persistence(self):
        for content in (b"", b"malware renamed .docx"):
            response = await self.client.post("/api/v1/applications/pre-review", data={"application_type": "meiyu_venue", "venue_id": "1"}, files={"file": ("wrong.docx", content)})
            self.assertEqual(response.status_code, 400)
        with patch.object(settings, "max_upload_size_mb", 0):
            self.assertEqual((await self.initial()).status_code, 413)
        response = await self.client.post("/api/v1/applications/pre-review", data={"application_type": "meiyu_venue", "venue_id": "1"}, files=[("file", ("a.docx", word_bytes()))] + [("additional_files", (f"{i}.pdf", b"%PDF-1.7")) for i in range(10)])
        self.assertEqual(response.status_code, 400)
        self.ai.assert_not_awaited()
        async with self.sessions() as db:
            self.assertFalse((await db.execute(select(Application))).scalars().all())

    async def test_selected_venue_date_and_conflict_validation(self):
        self.ai.return_value.venue_name = "错误场地"
        response = await self.initial()
        self.assertIn("VENUE_MISMATCH", [i["type"] for i in response.json()["issues"]])
        self.ai.return_value.venue_name = "会议室"
        self.ai.return_value.extracted_time_slots[0].start_at = datetime(2035,12,21,1,tzinfo=timezone.utc)
        response = await self.initial()
        self.assertIn("DATE_MISMATCH", [i["type"] for i in response.json()["issues"]])
        self.ai.return_value.extracted_time_slots[0].start_at = datetime(2035,12,20,1,tzinfo=timezone.utc)
        self.assertTrue((await self.initial()).json()["passed"])
        conflict = await self.initial()
        self.assertFalse(conflict.json()["passed"])
        self.assertTrue(conflict.json()["conflicts"])

    async def test_download_is_owner_only(self):
        app_id = (await self.initial()).json()["application_id"]
        file = (await self.client.get(f"/api/v1/applications/{app_id}/files")).json()[0]
        self.assertEqual((await self.client.get(file["download_url"])).status_code, 200)
        self.assertEqual((await self.client.get(file["download_url"], headers=self.headers(3))).status_code, 403)

    async def test_cancel_releases_reservation_and_admin_reason_is_visible(self):
        app_id = (await self.initial()).json()["application_id"]
        response = await self.client.post(f"/api/v1/applications/{app_id}/cancel")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "cancelled")
        async with self.sessions() as db:
            statuses = (await db.execute(select(ReservationCalendar.status))).scalars().all()
            self.assertEqual(statuses, ["cancelled"])
        app_id = (await self.initial()).json()["application_id"]
        await self.signed(app_id)
        response = await self.client.patch(f"/api/v1/admin/applications/{app_id}/status", headers=self.headers(2), json={"status":"rejected", "reason":"活动不符合场地用途"})
        self.assertEqual(response.status_code, 200, response.text)
        detail = (await self.client.get(f"/api/v1/applications/{app_id}")).json()
        self.assertEqual(detail["review_reason"], "活动不符合场地用途")
        self.assertEqual(detail["status"], "rejected")

    async def test_invalid_supplement_content_keeps_entire_batch_uncommitted(self):
        app_id = (await self.initial()).json()["application_id"]
        await self.signed(app_id)
        await self.request_supplement(app_id, ["meiyu_signed_application_form", "supporting_material"])
        response = await self.client.post(f"/api/v1/applications/{app_id}/files/batch", files=[
            ("file_types", (None, "meiyu_signed_application_form")), ("files", ("valid.pdf", b"%PDF-1.7")),
            ("file_types", (None, "supporting_material")), ("files", ("invalid.pdf", b"renamed executable"))])
        self.assertEqual(response.status_code, 400)
        material = (await self.client.get(f"/api/v1/applications/{app_id}/files")).json()
        self.assertEqual(len(material), 2)
        self.assertEqual((await self.client.get(f"/api/v1/applications/{app_id}")).json()["status"], "supplement_required")


if __name__ == "__main__":
    unittest.main()
