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
from app.models.key import KeyBorrowRecord
from app.models.notification import NotificationLog
from app.services.notification import NotificationService
from app.services.expiration import expiration_service
from app.api.routes.venues import build_calendar_event
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

    async def automatic(self):
        return await self.client.post("/api/v1/applications/pre-review", files={"file": ("application.docx", word_bytes())})

    async def test_document_only_submission_resolves_venue_and_checks_conflicts(self):
        response = await self.automatic()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["passed"])
        self.assertEqual(response.json()["venue_id"], 1)
        self.assertEqual(response.json()["application_type"], "meiyu_venue")
        self.assertEqual(self.ai.await_count, 1)
        self.assertEqual(self.ai.call_args.args[0], "auto")
        conflict = await self.automatic()
        self.assertFalse(conflict.json()["passed"])
        self.assertTrue(conflict.json()["conflicts"])

    async def test_auto_yueyuan_keeps_its_signed_material_workflow(self):
        self.ai.return_value.venue_name = "悦园三楼"
        response = await self.automatic()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["application_type"], "yueyuan_third_floor")
        self.assertEqual(response.json()["venue_id"], 2)
        self.assertEqual(response.json()["next_status"], "pending_signed_files")

    async def test_auto_unknown_venue_never_defaults_to_another_room(self):
        for name in (None, "未登记的房间"):
            self.ai.return_value.venue_name = name
            response = await self.automatic()
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['next_status'], 'pending_admin_pre_review')
            self.assertIsNone(response.json()['venue_id'])
        async with self.sessions() as db:
            self.assertEqual(len((await db.execute(select(Application))).scalars().all()), 2)
            self.assertEqual((await db.execute(select(ReservationCalendar))).scalars().all(), [])

    async def test_auto_ai_failure_queues_manual_review_without_reserving_a_room(self):
        self.ai.return_value = AiPreReviewResult(passed=False, issues=[ReviewIssue(type="AI_REVIEW_REQUEST_FAILED", message="test")])
        response = await self.automatic()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['next_status'], 'pending_admin_pre_review')

    def manual_decision(self, **overrides):
        return {'passed': True, 'venue_id': 1, 'borrow_organization': '人工核实组织',
                'time_slots': [{'start_at': '2035-12-20T09:00:00+08:00', 'end_at': '2035-12-20T11:00:00+08:00'}], **overrides}

    async def manual_application(self):
        self.ai.return_value = AiPreReviewResult(passed=False, issues=[ReviewIssue(type='AI_REVIEW_REQUEST_FAILED', message='timeout')])
        response = await self.automatic()
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['application_id']

    async def test_manual_fallback_emails_admin_and_can_finish_signed_review_without_ai(self):
        # Exercise the real notification logger, but never send actual email.
        real = NotificationService()
        with patch('app.services.notification.notification_service.notify_admins', side_effect=real.notify_admins), patch('app.services.notification.notification_service.send_and_log', side_effect=real.send_and_log):
            aid = await self.manual_application()
        async with self.sessions() as db:
            logs = (await db.execute(select(NotificationLog))).scalars().all()
            self.assertTrue(any(n.notification_type == 'pending_admin_pre_review' and n.recipient == 'admin@test.invalid' for n in logs))
            self.assertEqual((await db.execute(select(ReservationCalendar))).scalars().all(), [])
        path = f'/api/v1/admin/applications/{aid}/pre-review-decision'
        self.assertEqual((await self.client.post(path, json=self.manual_decision())).status_code, 403)
        self.assertEqual((await self.client.post(path, headers=self.headers(2), json={'passed':True})).status_code, 400)
        response = await self.client.post(path, headers=self.headers(2), json=self.manual_decision())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'pending_signed_files')
        self.assertEqual(len(response.json()['required_files']), 1)
        self.ai.reset_mock()
        response = await self.client.post(f'/api/v1/applications/{aid}/signed-files', files={'meiyu_signed_application_form':('signed.docx',word_bytes())})
        self.assertEqual(response.status_code,200,response.text)
        self.ai.assert_not_awaited()
        response = await self.client.patch(f'/api/v1/admin/applications/{aid}/status',headers=self.headers(2),json={'status':'submitted'})
        self.assertEqual(response.status_code,200,response.text)

    async def test_manual_review_rechecks_conflicts_and_yueyuan_day_rules(self):
        aid = await self.manual_application()
        path = f'/api/v1/admin/applications/{aid}/pre-review-decision'
        valid = self.manual_decision()
        self.assertEqual((await self.client.post(path, headers=self.headers(2), json=valid)).status_code, 200)
        other = await self.manual_application()
        path = f'/api/v1/admin/applications/{other}/pre-review-decision'
        response = await self.client.post(path, headers=self.headers(2), json=valid)
        self.assertEqual(response.status_code,409,response.text)
        consecutive = self.manual_decision(venue_id=2,time_slots=valid['time_slots']+[{'start_at':'2035-12-21T09:00:00+08:00','end_at':'2035-12-21T11:00:00+08:00'}])
        self.assertEqual((await self.client.post(path, headers=self.headers(2), json=consecutive)).status_code,400)

    async def test_manual_rejection_without_venue_can_be_resubmitted_and_failed_service_preserves_metadata(self):
        aid = await self.manual_application()
        path = f'/api/v1/admin/applications/{aid}/pre-review-decision'
        self.assertEqual((await self.client.post(path,headers=self.headers(2),json={'passed':False,'reason':'请写明时间'})).status_code,200)
        self.ai.return_value = AiPreReviewResult(passed=True,venue_name='会议室',borrow_organization='材料中的社团',applicant_name='测试甲',extracted_time_slots=[ExtractedTimeSlot(date='2035-12-20',start_time='09:00',end_time='11:00',start_at=datetime(2035,12,20,1,tzinfo=timezone.utc),end_at=datetime(2035,12,20,3,tzinfo=timezone.utc))])
        response = await self.client.post(f'/api/v1/applications/{aid}/pre-review',files={'file':('retry.docx',word_bytes())})
        self.assertEqual(response.json()['next_status'],'pending_signed_files',response.text)
        rejected = (await self.automatic()).json()['application_id']
        old = (await self.client.get(f'/api/v1/applications/{rejected}')).json()
        self.ai.return_value = AiPreReviewResult(passed=False,issues=[ReviewIssue(type='AI_RESPONSE_PARSE_FAILED',message='bad response')])
        response = await self.client.post(f'/api/v1/applications/{rejected}/pre-review',files={'file':('retry.docx',word_bytes())})
        self.assertEqual(response.json()['next_status'],'pending_admin_pre_review')
        detail = (await self.client.get(f'/api/v1/applications/{rejected}')).json()
        self.assertEqual(detail['borrow_organization'],old['borrow_organization'])
        self.assertEqual(detail['start_at'],old['start_at'])
        self.assertNotIn('MISSING_TIME_SLOT',detail['review_reason'])
        versions = (await self.client.get(f'/api/v1/applications/{rejected}/files')).json()
        self.assertEqual([f['version'] for f in versions],[2,1])
        self.assertEqual(versions[0]['review_status'],'pending_admin_review')

    async def test_key_submission_is_manual_accepts_scan_and_requires_admin_details(self):
        with patch('app.services.key_ai_review.key_ai_review_service.extract_key_borrow_info',new_callable=AsyncMock) as key_ai:
            response = await self.client.post('/api/v1/keys/borrow',files={'file':('scan.pdf',b'%PDF-1.7 simulated scan')})
            self.assertEqual(response.status_code,200,response.text)
            key_ai.assert_not_awaited()
        aid=response.json()['application_id']
        path=f'/api/v1/admin/applications/{aid}/status'
        response=await self.client.patch(path,headers=self.headers(2),json={'status':'submitted'})
        self.assertEqual(response.status_code,400,response.text)
        payload={'status':'submitted','key_details':{'borrowed_key_name':'会议室钥匙','borrow_organization':'人工组织','start_at':'2035-12-20T09:00:00+08:00','end_at':'2035-12-20T11:00:00+08:00'}}
        response=await self.client.patch(path,headers=self.headers(2),json=payload)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['borrowed_key_name'],'会议室钥匙')
        async with self.sessions() as db:
            record=(await db.execute(select(KeyBorrowRecord).where(KeyBorrowRecord.application_id==aid))).scalar_one()
            self.assertEqual(record.borrow_organization,'人工组织')

    async def test_expiration_is_timezone_safe_and_idempotent(self):
        async with self.sessions() as db:
            application=Application(user_id=1,venue_id=2,application_type='yueyuan_third_floor',status='pending_signed_files',start_at=datetime(2035,12,20,9),end_at=datetime(2035,12,20,11))
            db.add(application);await db.commit()
        real=NotificationService()
        with patch('app.services.notification.notification_service.send_and_log',side_effect=real.send_and_log):
            async with self.sessions() as db:
                result=await expiration_service.process_yueyuan_pending_signed_files(db,datetime(2035,12,17,2,tzinfo=timezone.utc))
                self.assertEqual(result,{'reminded':1,'cancelled':0})
                self.assertEqual(await expiration_service.process_yueyuan_pending_signed_files(db,datetime(2035,12,17,2,tzinfo=timezone.utc)),{'reminded':0,'cancelled':0})
                self.assertEqual(await expiration_service.process_yueyuan_pending_signed_files(db,datetime(2035,12,18,2,tzinfo=timezone.utc)),{'reminded':0,'cancelled':1})

    async def test_auto_rejected_material_stays_rejected(self):
        self.ai.return_value.passed = False
        self.ai.return_value.issues = [ReviewIssue(type="MISSING_INFO", message="缺少组织")]
        response = await self.automatic()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["next_status"], "ai_rejected")
        async with self.sessions() as db:
            self.assertEqual((await db.execute(select(ReservationCalendar))).scalars().all(), [])

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

    async def test_manual_fallback_survives_email_failure_and_all_service_errors(self):
        service = NotificationService()
        with patch('app.api.routes.applications.notification_service', service), patch(
            'app.services.email.email_service.send_text_email', side_effect=RuntimeError('simulated SMTP unavailable')
        ), patch.object(settings, 'admin_notification_email_csv', ''):
            for issue in ('AI_REVIEW_REQUEST_FAILED', 'AI_REVIEW_NOT_CONFIGURED', 'AI_RESPONSE_PARSE_FAILED'):
                self.ai.return_value = AiPreReviewResult(passed=False, issues=[ReviewIssue(type=issue, message='test')])
                result = await self.client.post('/api/v1/applications/pre-review', files={'file': ('test.docx', word_bytes())})
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()['next_status'], 'pending_admin_pre_review')
            async with self.sessions() as db:
                self.assertEqual(len((await db.execute(select(Application))).scalars().all()), 3)
                self.assertEqual(len((await db.execute(select(ApplicationFile))).scalars().all()), 3)
                logs = (await db.execute(select(NotificationLog))).scalars().all()
                self.assertEqual([log.status for log in logs if log.recipient == 'admin@test.invalid'], ['failed'] * 3)
                self.assertTrue(all(log.status == 'failed' for log in logs))
                self.assertFalse((await db.execute(select(ReservationCalendar))).scalars().all())

    async def test_calendar_china_timezone_and_cross_month_midnight(self):
        utc_reservation = ReservationCalendar(id=10, application_id=10, venue_id=1,
            start_at=datetime(2035,12,20,1,tzinfo=timezone.utc), end_at=datetime(2035,12,20,3,tzinfo=timezone.utc), status='confirmed')
        event = build_calendar_event(utc_reservation, None, Venue(id=1,name='会议室',venue_type='meiyu'))
        self.assertEqual(event.start_at.isoformat(), '2035-12-20T09:00:00+08:00')
        self.assertEqual(event.end_at.isoformat(), '2035-12-20T11:00:00+08:00')
        async with self.sessions() as db:
            app = Application(user_id=1,venue_id=1,application_type='meiyu_venue',status='submitted')
            db.add(app)
            await db.flush()
            db.add(ReservationCalendar(application_id=app.id,venue_id=1,status='confirmed',
                start_at=datetime(2035,11,30,23),end_at=datetime(2035,12,2,0)))
            await db.commit()
        data = (await self.client.get('/api/v1/venues/1/calendar?year=2035&month=12')).json()
        self.assertEqual(data['days']['2035-12-01']['segments'][0]['start_time'], '00:00')
        self.assertEqual(data['days']['2035-12-01']['segments'][0]['end_time'], '24:00')
        self.assertEqual(data['days']['2035-12-02']['event_count'], 0)
        data = (await self.client.get('/api/v1/venues/usage-range?start_date=2035-12-02&end_date=2035-12-02')).json()
        self.assertFalse(any(venue['events'] for venue in data['venues']))

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
