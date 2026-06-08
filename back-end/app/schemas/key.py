from datetime import datetime

from pydantic import BaseModel, Field


class KeyResourceRead(BaseModel):
    id: int
    name: str
    room_name: str | None
    status: str

    model_config = {"from_attributes": True}


class KeyBorrowResponse(BaseModel):
    application_id: int
    borrowed_key_name: str | None
    status: str
    borrowed_at: datetime | None
    expected_return_at: datetime | None
    ai_issues: list[str] = []
    uploaded_file_version: int


class KeyResourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    room_name: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=32)


class KeyBorrowAiResult(BaseModel):
    borrowed_key_name: str | None = None
    borrowed_at: datetime | None = None
    expected_return_at: datetime | None = None
    issues: list[str] = []
    raw_result: dict | None = None
