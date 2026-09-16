# MeiyuSystem Back End

FastAPI backend for the venue application, key borrowing, SDU authentication, AI review, file versioning, email notification, and admin workflows.

## Environment

Use the existing conda environment:

```sh
conda activate fastapi
pip install -r requirements.txt
```

Copy environment variables:

```sh
cp .env.example .env
```

Set local secrets in `.env`. The AI pre-review service uses an OpenAI-compatible chat completions endpoint:

```env
AI_API_BASE_URL=https://llm.zerohyh.top/v1
AI_API_KEY=your-api-key
AI_MODEL=Ali-dashscope/MiniMax-M2.5
```

The base URL may include `/v1` or just the server root. The backend appends
`/chat/completions` without duplicating the version prefix.

Run locally:

```sh
uvicorn app.main:app --reload
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Application Templates

Front-end clients can fetch downloadable application templates from:

```text
GET /api/v1/templates
GET /api/v1/templates/{template_id}/download
```

The list endpoint returns template metadata and a stable `download_url`.

## Structure

```text
app/
  api/routes/       HTTP route modules
  core/             settings and security helpers
  db/               database session and base model
  models/           SQLAlchemy models
  schemas/          Pydantic schemas
  services/         business service integrations
alembic/            database migrations
```

## Authentication

System login uses JWT.

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
PATCH /api/v1/auth/me/organization
```

`register` and `login` return:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "role": "user",
    "is_sdu_verified": false,
    "is_application_allowed": false
  }
}
```

Authenticated requests should include:

```http
Authorization: Bearer <access_token>
```

When the access token expires, call `/api/v1/auth/refresh` with the refresh token to get a new token pair. Logout is handled by the frontend by removing the local access token and refresh token.

Users can update their organization with:

```http
PATCH /api/v1/auth/me/organization
Authorization: Bearer <access_token>
Content-Type: application/json
```

```json
{
  "organization": "美育协会"
}
```

The backend stores this value in `User.department`, which is used as the user's default organization/department information.

`/auth/login` accepts a registered email, verified mobile number, or verified SDU ID:

```json
{
  "account": "202400000000",
  "password": "your-password"
}
```

SDU ID login becomes available only after the user completes SDU authentication and the ID is saved in `AuthProfile`. Set `INITIAL_ADMIN_ACCOUNT` and `INITIAL_ADMIN_PASSWORD` explicitly to bootstrap an administrator; there are no fallback credentials. Production seeding does not create demo applications.

## SDU Authentication

SDU authentication is a profile binding flow for the currently logged-in user, so all endpoints require:

```http
Authorization: Bearer <access_token>
```

Flow:

```text
POST /api/v1/sdu-auth/code
POST /api/v1/sdu-auth/sms
POST /api/v1/sdu-auth/login
```

`/code` returns the image captcha and sets a temporary `login_session` cookie.

`/sms` expects:

```json
{
  "mobile": "13800000000",
  "code": "1234"
}
```

`/login` expects:

```json
{
  "mobile": "13800000000",
  "code": "123456",
  "department": "美育协会"
}
```

After SDU login succeeds, the backend saves or updates `AuthProfile`, writes `department` to the current user, marks the user as `is_sdu_verified=true`, and returns the verified SDU profile.

## Venue Calendar

Venue list:

```text
GET /api/v1/venues
```

Monthly venue calendar endpoint:

```text
GET /api/v1/venues/{venue_id}/calendar?year=2026&month=6
```

The response is optimized for the frontend layout:

- `events`: flat event list for rendering the month calendar.
- `days`: date-keyed index for the selected-day detail panel.
- `legend`: status colors for the calendar legend.

Example shape:

```json
{
  "year": 2026,
  "month": 6,
  "timezone": "Asia/Shanghai",
  "month_start": "2026-06-01",
  "month_end": "2026-06-30",
  "venue": {
    "id": 1,
    "name": "悦园三楼",
    "venue_type": "yueyuan_third_floor"
  },
  "events": [
    {
      "id": "app-1001-0",
      "application_id": 1001,
      "venue_id": 1,
      "venue_name": "悦园三楼",
      "application_type": "yueyuan_third_floor",
      "title": "美育协会活动",
      "organization": "美育协会",
      "applicant_name": "张三",
      "start_at": "2026-06-12T12:00:00+08:00",
      "end_at": "2026-06-12T19:10:00+08:00",
      "status": "confirmed",
      "occupancy_type": "confirmed",
      "is_mine": false,
      "color": "#2563eb"
    }
  ],
  "days": {
    "2026-06-12": {
      "date": "2026-06-12",
      "is_today": false,
      "event_count": 1,
      "has_available_slots": true,
      "segments": [
        {
          "event_id": "app-1001-0",
          "start_time": "12:00",
          "end_time": "19:10",
          "status": "confirmed",
          "occupancy_type": "confirmed",
          "title": "美育协会活动"
        }
      ]
    }
  }
}
```

## Application Pre-review

Users submit Word documents for AI pre-review:

```text
POST /api/v1/applications/pre-review
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

Form fields:

```text
application_type=auto (default)
file=<.docx Word document>
```

The user-facing flow goes straight to the envelope and accepts one DOCX, without
a venue/date form or optional supporting-material upload. AI identifies the venue
and dates from the document; the backend resolves the venue against the catalog
and determines the application type. Unknown/ambiguous venues and AI service
failures save the material and return `next_status=pending_admin_pre_review`,
notifying administrators without creating a reservation. A successful upload to
this queue has `passed=false` because review has not finished; it is not a material
rejection and should not prompt the user to upload again. Document times use Asia/Shanghai.

For older clients, explicit `venue_id`, `application_type` (`meiyu_venue` or
`yueyuan_third_floor`), `expected_date`, and repeatable `additional_files` remain
supported. Explicit venue/date values are still cross-checked against the document.

Flow:

```text
Upload Word document
-> backend extracts paragraphs and table text from .docx
-> backend uses the automatic venue-review prompt (including Yueyuan planning rules)
-> AI extracts structured venue/time/application info
-> backend matches the venue to a real catalog entry and determines application_type
-> backend checks time conflicts against ReservationCalendar
-> if passed, backend creates Application, stores the Word file, and writes pre_reserved calendar records
-> if rejected, backend stores the reason with status ai_rejected and does not occupy the calendar
-> backend returns extracted times, issues, conflicts, next_status, and application_id
```

AI performs the initial document review. Time conflict checking is always performed by the backend.
An AI-rejected application does not wait for manual pre-review. The user can read
`review_reason` from the application list and resubmit a corrected Word file:

```text
POST /api/v1/applications/{application_id}/pre-review
file=<corrected .docx Word document>
additional_files=<optional supporting document, repeatable>
```

Every resubmission creates a new `pre_review_word` file version.

When pre-review passes, the application stores a snapshot of:

- current user id
- applicant name from `AuthProfile`
- applicant SDU ID from `AuthProfile`
- applicant department from `User.department`
- borrow organization extracted by AI
- legacy `organization`, synchronized from borrow organization for list/calendar display
- purpose summary extracted by AI

User application list:

```text
GET /api/v1/applications
GET /api/v1/applications?status_filter=pending_admin_submit
```

`POST /api/v1/applications` is intentionally not used. Applications are created by specific workflows such as pre-review and key borrowing.

User cancellation:

```text
POST   /api/v1/applications/{application_id}/cancel
DELETE /api/v1/applications/{application_id}
```

Both endpoints perform a soft cancellation. The application record is kept, its status becomes `cancelled`, and related venue calendar entries are marked `cancelled` so the time is released. Users can cancel their own applications before the earliest usage start time, including applications already submitted successfully by an administrator. Cancelled, rejected, or completed applications cannot be cancelled again.

## Signed Files

After pre-review passes, users submit signed and stamped files:

```text
POST /api/v1/applications/{application_id}/signed-files
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

Meiyu venue requires one file:

```text
meiyu_signed_application_form=<signed and stamped application form>
```

Yueyuan third floor requires the normal files plus scanned signed/stamped pages:

```text
yueyuan_plan_file=<normal plan file>
yueyuan_plan_signed_scan=<signed/stamped scan page>
safety_responsibility_file=<normal safety responsibility file>
safety_responsibility_signed_scan=<signed/stamped scan page>
work_checklist_file=<normal work checklist file>
work_checklist_signed_scan=<signed/stamped scan page>
electricity_commitment_file=<normal electricity commitment file>
electricity_commitment_signed_scan=<signed/stamped scan page>
```

Every upload creates a new `ApplicationFile` version. Existing files are not overwritten.

After all required files are saved, the application status becomes:

```text
pending_admin_submit
```

Supplement file upload:

```text
POST /api/v1/applications/{application_id}/files
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

Form fields:

```text
file_type=<requested file type>
file=<supplement file>
```

This endpoint is only available when the application status is `supplement_required`.

The staged multi-file frontend confirms all supplement files with one atomic request:

```text
POST /api/v1/applications/{application_id}/files/batch
file_type=supplement_file
files=<supplement file, repeatable>
```

The application status changes only after every file in the batch has been saved.

Application file list and download:

```text
GET /api/v1/applications/{application_id}/files
GET /api/v1/applications/{application_id}/files/{file_id}/download
```

Only the application owner or an administrator can access uploaded files.

## Key Borrowing

Key resource list:

```text
GET /api/v1/keys
```

Create key borrowing application:

```text
POST /api/v1/keys/borrow
Content-Type: multipart/form-data
Authorization: Bearer <access_token>
```

Form fields:

```text
file=<PDF scanned key borrowing application>
```

The endpoint saves the PDF and creates a `key_borrow` application in `pending_admin_submit`, notifying administrators by email. It does not call AI or require OCR; image-only scanned PDFs are accepted. Administrators must read the original and supply `key_details` (borrowed_key_name, borrow_organization, start_at, end_at) when confirming via the status endpoint. Empty metadata cannot be approved.

## Admin APIs

Admin application list:

```text
GET /api/v1/admin/applications
GET /api/v1/admin/applications?status_filter=pending_admin_submit
GET /api/v1/admin/applications?application_type=meiyu_venue
```

Update application status:

```text
PATCH /api/v1/admin/applications/{application_id}/status
```

Supported statuses:

```text
pending_signed_files
pending_admin_submit
submitted
completed
cancelled
rejected
```

AI request/configuration/response failures and unresolved venues enter `pending_admin_pre_review` and notify administrators by email, rather than rejecting the user's materials. These applications do not reserve a venue until manual approval. Signed Word/PDF materials are also reviewed manually without AI.

Manual initial review (requires complete metadata; rechecks time conflicts and Yueyuan date rules):

```text
POST /api/v1/admin/applications/{application_id}/pre-review-decision
```

```json
{
  "passed": true,
  "reason": "人工确认材料可通过初审。",
  "venue_id": 1,
  "borrow_organization": "申请组织",
  "time_slots": [{"start_at": "2035-12-20T09:00:00+08:00", "end_at": "2035-12-20T11:00:00+08:00"}]
}
```

Request supplement files and notify the user:

```text
POST /api/v1/admin/applications/{application_id}/request-supplement
```

```json
{
  "file_types": ["yueyuan_plan_signed_scan"],
  "reason": "签字盖章页不清晰，请重新上传。"
}
```

Manually allow an unverified user to apply:

```text
POST /api/v1/admin/users/{user_id}/allow-application
```

User management:

```text
GET /api/v1/admin/users
PATCH /api/v1/admin/users/{user_id}
```

Run Yueyuan third floor pending-file expiration checks:

```text
POST /api/v1/admin/maintenance/process-expirations
```

For scheduled execution, run this command from the backend directory via cron:

```sh
conda run -n fastapi python -m app.tasks.process_expirations
```

Seed venues and the initial admin:

```sh
conda run -n fastapi python -m app.db.seed
```

Current parser support:

- `.docx`: supported, including paragraphs and table text.
- `.doc`: not supported yet. Convert to `.docx` before upload.

Response shape:

```json
{
  "passed": false,
  "application_type": "yueyuan_third_floor",
  "venue_id": 1,
  "next_status": "pending_admin_pre_review",
  "extracted_time_slots": [
    {
      "date": "2026-06-12",
      "start_time": "12:00",
      "end_time": "19:10",
      "start_at": "2026-06-12T12:00:00+08:00",
      "end_at": "2026-06-12T19:10:00+08:00"
    }
  ],
  "issues": [],
  "conflicts": [
    {
      "venue_id": 1,
      "application_id": 1001,
      "start_at": "2026-06-12T12:00:00+08:00",
      "end_at": "2026-06-12T19:10:00+08:00",
      "status": "confirmed",
      "message": "申请时间与已有预约冲突"
    }
  ],
  "application_id": 1002,
  "purpose_summary": "用于举办学院文艺汇演活动。"
}
```
