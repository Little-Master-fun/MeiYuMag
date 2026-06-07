from datetime import datetime

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    type: str
    message: str


class ExtractedTimeSlot(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    start_time: str = Field(description="HH:mm")
    end_time: str = Field(description="HH:mm")
    start_at: datetime | None = None
    end_at: datetime | None = None


class AiPreReviewResult(BaseModel):
    passed: bool
    venue_name: str | None = None
    organization: str | None = None
    purpose_summary: str | None = None
    applicant_name: str | None = None
    extracted_time_slots: list[ExtractedTimeSlot] = []
    issues: list[ReviewIssue] = []
    raw_result: dict | None = None


class ConflictItem(BaseModel):
    venue_id: int
    application_id: int | None = None
    start_at: datetime
    end_at: datetime
    status: str
    message: str


class ApplicationPreReviewResponse(BaseModel):
    passed: bool
    application_type: str
    venue_id: int
    next_status: str
    extracted_time_slots: list[ExtractedTimeSlot]
    issues: list[ReviewIssue]
    conflicts: list[ConflictItem]
    application_id: int | None = None
    purpose_summary: str | None = None


class ApplicationRead(BaseModel):
    id: int
    user_id: int
    application_type: str
    organization: str | None
    purpose_summary: str | None
    applicant_name: str | None
    applicant_sduid: str | None
    applicant_department: str | None
    venue_id: int | None
    key_id: int | None
    status: str
    start_at: datetime | None
    end_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationFileRead(BaseModel):
    id: int
    application_id: int
    file_type: str
    version: int
    original_filename: str
    review_status: str
    reject_reason: str | None
    created_at: datetime
    download_url: str

    model_config = {"from_attributes": True}


class UploadedSignedFile(BaseModel):
    file_type: str
    version: int
    original_filename: str


class SignedFilesSubmitResponse(BaseModel):
    application_id: int
    application_type: str
    status: str
    uploaded_files: list[UploadedSignedFile]


class SupplementRequest(BaseModel):
    file_types: list[str] = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=1000)


class SupplementRequestResponse(BaseModel):
    application_id: int
    status: str
    requested_file_types: list[str]
    reason: str
    notification_status: str


class GenericFileUploadResponse(BaseModel):
    application_id: int
    status: str
    uploaded_file: UploadedSignedFile


class AdminApplicationStatusUpdate(BaseModel):
    status: str = Field(
        description=(
            "Supported values: pending_signed_files, pending_admin_submit, "
            "submitted, completed, cancelled, rejected"
        )
    )
    reason: str | None = Field(default=None, max_length=1000)


class AdminPreReviewDecision(BaseModel):
    passed: bool
    reason: str | None = Field(default=None, max_length=1000)
