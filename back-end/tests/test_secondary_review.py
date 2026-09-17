"""Role boundaries and signing handoff, with isolated DB/files and mocked mail."""
import unittest
from unittest.mock import patch

from sqlalchemy import select

import test_application_workflow as workflow
from app.core.config import settings
from app.models import Application, ApplicationFile, User, ReservationCalendar
from app.models.notification import NotificationLog
from app.models.auth_profile import AuthProfile
from app.services.notification import NotificationService


class SecondaryReviewTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = workflow.WorkflowTests.asyncSetUp
    asyncTearDown = workflow.WorkflowTests.asyncTearDown
    headers = workflow.WorkflowTests.headers
    automatic = workflow.WorkflowTests.automatic
    signed = workflow.WorkflowTests.signed
    manual_application = workflow.WorkflowTests.manual_application

    async def appoint(self, uid=3, role="secondary_admin"):
        response = await self.client.patch(f"/api/v1/admin/users/{uid}", headers=self.headers(2), json={"role": role})
        self.assertEqual(response.status_code, 200, response.text)

    async def ready(self):
        aid = (await self.automatic()).json()["application_id"]
        response = await self.signed(aid)
        self.assertEqual(response.status_code, 200, response.text)
        return aid

    async def decision(self, aid, passed=True, uid=3, reason=None):
        return await self.client.post(f"/api/v1/secondary/applications/{aid}/decision", headers=self.headers(uid), json={"passed": passed, "reason": reason})

    async def scan(self, aid, uid=3, filename="countersigned.pdf", content=b"%PDF-1.7 test scan"):
        return await self.client.post(f"/api/v1/secondary/applications/{aid}/countersigned-file", headers=self.headers(uid), files={"file": (filename, content)})

    async def test_all_users_primary_only_and_role_management(self):
        users = await self.client.get('/api/v1/admin/users', headers=self.headers(2))
        self.assertEqual(len(users.json()), 3)
        self.assertNotIn('password_hash', users.json()[0])
        await self.appoint()
        for uid in (1, 3):
            for endpoint in ('users', 'applications'):
                self.assertEqual((await self.client.get('/api/v1/admin/' + endpoint, headers=self.headers(uid))).status_code, 403)
            self.assertEqual((await self.client.patch('/api/v1/admin/users/1', headers=self.headers(uid), json={'role': 'admin'})).status_code, 403)
        self.assertEqual((await self.client.patch('/api/v1/admin/users/2', headers=self.headers(2), json={'role': 'user'})).status_code, 409)
        self.assertEqual((await self.client.get('/api/v1/secondary/applications')).status_code, 403)

    async def test_primary_roster_includes_only_the_verified_profile_name(self):
        async with self.sessions() as db:
            db.add(AuthProfile(user_id=1, sduid='test-sdu-1', name='认证测试甲', mobile='13800000000'))
            await db.commit()
        response = await self.client.get('/api/v1/admin/users', headers=self.headers(2))
        self.assertEqual(response.status_code, 200, response.text)
        users = {user['id']: user for user in response.json()}
        self.assertEqual(users[1]['verified_name'], '认证测试甲')
        self.assertIsNone(users[2]['verified_name'])  # Accounts without a profile remain listed.
        self.assertIsNone(users[3]['verified_name'])
        for user in users.values():
            self.assertEqual(set(user), {'id', 'email', 'role', 'department', 'is_sdu_verified', 'is_application_allowed', 'verified_name'})
        # Editing the role or granting access must not lose the name in the UI.
        response = await self.client.patch('/api/v1/admin/users/1', headers=self.headers(2), json={'role':'secondary_admin'})
        self.assertEqual(response.json()['verified_name'], '认证测试甲')
        response = await self.client.post('/api/v1/admin/users/1/allow-application', headers=self.headers(2))
        self.assertEqual(response.json()['verified_name'], '认证测试甲')
        response = await self.client.get('/api/v1/admin/users?role=secondary_admin', headers=self.headers(2))
        self.assertEqual([(user['id'], user['verified_name']) for user in response.json()], [(1, '认证测试甲')])
        # Keep this field out of the shared login/profile response schema.
        response = await self.client.get('/api/v1/auth/me', headers=self.headers(1))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('verified_name', response.json())

    async def test_verified_name_admin_endpoints_reject_non_primary_roles(self):
        await self.appoint()
        for uid in (1, 3):
            self.assertEqual((await self.client.get('/api/v1/admin/users', headers=self.headers(uid))).status_code, 403)
            self.assertEqual((await self.client.post('/api/v1/admin/users/1/allow-application', headers=self.headers(uid))).status_code, 403)
            self.assertEqual((await self.client.patch('/api/v1/admin/users/1', headers=self.headers(uid), json={'is_application_allowed':True})).status_code, 403)
        response = await self.client.get('/api/v1/admin/users', headers={'Authorization':'Bearer invalid'})
        self.assertEqual(response.status_code, 401)

    async def test_full_secondary_handoff_and_scoped_downloads(self):
        await self.appoint()
        aid = await self.ready()
        detail = (await self.client.get(f'/api/v1/applications/{aid}')).json()
        self.assertEqual(detail['status'], 'pending_secondary_review')
        self.assertEqual(detail['secondary_reviewer_id'], 3)
        queue = await self.client.get('/api/v1/secondary/applications', headers=self.headers(3))
        self.assertEqual([a['id'] for a in queue.json()], [aid])
        files = (await self.client.get(f'/api/v1/applications/{aid}/files', headers=self.headers(3))).json()
        self.assertEqual((await self.client.get(files[0]['download_url'], headers=self.headers(3))).status_code, 200)
        path = f'/api/v1/admin/applications/{aid}/status'
        self.assertEqual((await self.client.patch(path, headers=self.headers(2), json={'status': 'submitted'})).status_code, 409)
        self.assertEqual((await self.scan(aid)).status_code, 409)
        response = await self.decision(aid)
        self.assertEqual(response.json()['status'], 'pending_secondary_signature', response.text)
        self.assertEqual((await self.decision(aid)).status_code, 409)
        self.assertEqual((await self.scan(aid, uid=1)).status_code, 403)
        self.assertEqual((await self.scan(aid, filename='wrong.docx', content=workflow.word_bytes())).status_code, 400)
        self.assertEqual((await self.scan(aid, content=b'not a pdf')).status_code, 400)
        response = await self.scan(aid)
        self.assertEqual(response.json()['status'], 'pending_admin_submit', response.text)
        self.assertEqual((await self.scan(aid)).status_code, 409)
        self.assertEqual((await self.client.patch(path, headers=self.headers(3), json={'status': 'submitted'})).status_code, 403)
        self.assertEqual((await self.client.patch(path, headers=self.headers(2), json={'status': 'submitted'})).status_code, 200)
        self.assertEqual(self.ai.await_count, 1)  # Only the initial Word review.
        async with self.sessions() as db:
            reserved = (await db.execute(select(ReservationCalendar))).scalars().one()
            self.assertEqual(reserved.status, 'confirmed')

    async def test_unassigned_secondary_cannot_read_or_decide_and_no_self_review(self):
        await self.appoint()
        async with self.sessions() as db:
            db.add(User(id=4, email='second@test.invalid', password_hash='unused', role='secondary_admin'))
            await db.commit()
        aid = await self.ready()
        files = (await self.client.get(f'/api/v1/applications/{aid}/files')).json()
        for path in (f'/api/v1/applications/{aid}', f'/api/v1/applications/{aid}/files', files[0]['download_url']):
            self.assertEqual((await self.client.get(path, headers=self.headers(4))).status_code, 403)
        self.assertEqual((await self.decision(aid, uid=4)).status_code, 403)
        self.assertEqual((await self.client.get('/api/v1/secondary/applications', headers=self.headers(4))).json(), [])
        # Applicant becoming a secondary admin still cannot review their own work.
        await self.appoint(1)
        self.assertEqual((await self.decision(aid, uid=1)).status_code, 403)
        self.assertEqual((await self.client.get('/api/v1/applications', headers=self.headers(1))).json()[0]['id'], aid)

    async def test_no_secondary_or_only_applicant_keeps_primary_workflow(self):
        await self.appoint(1)
        aid = await self.ready()
        detail = (await self.client.get(f'/api/v1/applications/{aid}')).json()
        self.assertEqual(detail['status'], 'pending_admin_submit')
        self.assertIsNone(detail['secondary_reviewer_id'])
        self.assertEqual((await self.client.patch(f'/api/v1/admin/applications/{aid}/status', headers=self.headers(2), json={'status':'submitted'})).status_code, 200)

    async def test_return_correct_resubmit_and_no_countersign_bypass(self):
        await self.appoint()
        aid = await self.ready()
        self.assertEqual((await self.decision(aid, False)).status_code, 400)
        response = await self.decision(aid, False, reason='请补齐签字页')
        self.assertEqual(response.json()['status'], 'supplement_required')
        self.assertEqual(response.json()['required_files'][0]['file_type'], 'meiyu_signed_application_form')
        response = await self.client.post(f'/api/v1/applications/{aid}/files/batch', data={'file_types':'meiyu_signed_application_form'}, files={'files':('corrected.pdf',b'%PDF-1.7 scan')})
        self.assertEqual(response.json()['status'], 'pending_secondary_review', response.text)
        await self.decision(aid)
        await self.scan(aid)
        # Primary asks applicant to fix again; a prior countersign cannot be reused.
        await self.client.post(f'/api/v1/admin/applications/{aid}/request-supplement', headers=self.headers(2), json={'file_types':['meiyu_signed_application_form'], 'reason':'需重新签字'})
        response = await self.client.post(f'/api/v1/applications/{aid}/files', data={'file_type':'meiyu_signed_application_form'}, files={'file':('corrected.pdf',b'%PDF-1.7 scan')})
        self.assertEqual(response.json()['status'], 'pending_secondary_review')
        async with self.sessions() as db:
            scan = (await db.execute(select(ApplicationFile).where(ApplicationFile.file_type=='meiyu_countersigned_scan'))).scalar_one()
            self.assertEqual(scan.review_status, 'rejected')
        await self.decision(aid)
        await self.scan(aid)
        versions = (await self.client.get(f'/api/v1/applications/{aid}/files')).json()
        self.assertEqual([f['version'] for f in versions if f['file_type']=='meiyu_countersigned_scan'], [2,1])

    async def test_revocation_reassigns_then_falls_back_and_revokes_downloads(self):
        await self.appoint()
        async with self.sessions() as db:
            db.add(User(id=4, email='second@test.invalid', password_hash='unused', role='secondary_admin'))
            await db.commit()
        aid = await self.ready()
        await self.decision(aid)
        await self.appoint(3, 'user')
        detail = (await self.client.get(f'/api/v1/applications/{aid}')).json()
        self.assertEqual(detail['secondary_reviewer_id'], 4)
        self.assertEqual(detail['status'], 'pending_secondary_review')
        self.assertEqual((await self.client.get(f'/api/v1/applications/{aid}/files', headers=self.headers(3))).status_code, 403)
        await self.appoint(4, 'user')
        detail = (await self.client.get(f'/api/v1/applications/{aid}')).json()
        self.assertIsNone(detail['secondary_reviewer_id'])
        self.assertEqual(detail['status'], 'pending_admin_submit')

    async def test_cancellation_blocks_secondary_actions(self):
        await self.appoint()
        aid = await self.ready()
        self.assertEqual((await self.client.post(f'/api/v1/applications/{aid}/cancel')).status_code, 200)
        self.assertEqual((await self.decision(aid)).status_code, 409)
        self.assertEqual((await self.scan(aid)).status_code, 409)

    async def test_key_and_yueyuan_never_enter_secondary_queue(self):
        await self.appoint()
        response = await self.client.post('/api/v1/keys/borrow', files={'file':('key.pdf',b'%PDF-1.7 scan')})
        key_id = response.json()['application_id']
        self.assertEqual((await self.client.get(f'/api/v1/applications/{key_id}', headers=self.headers(3))).status_code, 403)
        self.ai.return_value.venue_name = '悦园三楼'
        aid = (await self.automatic()).json()['application_id']
        response = await self.signed(aid, workflow.signed_file_types('yueyuan_third_floor'))
        self.assertEqual(response.json()['status'], 'pending_admin_submit')
        self.assertEqual((await self.client.get('/api/v1/secondary/applications', headers=self.headers(3))).json(), [])

    async def test_mail_routes_ai_failure_to_primary_and_signed_steps_to_correct_recipient(self):
        await self.appoint()
        real = NotificationService()
        with patch('app.services.notification.notification_service.notify_admins', side_effect=real.notify_admins), patch('app.services.notification.notification_service.send_and_log', side_effect=real.send_and_log), patch.object(settings, 'admin_notification_emails', ['other@test.invalid']):
            await self.manual_application()
            self.ai.return_value = workflow.AiPreReviewResult(passed=True, venue_name='会议室', borrow_organization='测试组织', extracted_time_slots=[workflow.ExtractedTimeSlot(date='2035-12-20',start_time='09:00',end_time='11:00',start_at=workflow.datetime(2035,12,20,1,tzinfo=workflow.timezone.utc),end_at=workflow.datetime(2035,12,20,3,tzinfo=workflow.timezone.utc))])
            aid = await self.ready()
            await self.decision(aid)
            await self.scan(aid)
        async with self.sessions() as db:
            logs = (await db.execute(select(NotificationLog))).scalars().all()
            recipients = lambda kind: {log.recipient for log in logs if log.notification_type == kind}
            self.assertEqual(recipients('pending_admin_pre_review'), {'admin@test.invalid'})
            self.assertEqual(recipients('pending_secondary_review'), {'other@test.invalid'})
            self.assertEqual(recipients('secondary_signature_completed'), {'admin@test.invalid'})
