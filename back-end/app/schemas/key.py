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
    key_id: int
    status: str
    borrowed_at: datetime | None
    expected_return_at: datetime | None
    uploaded_file_version: int


class KeyReturnResponse(BaseModel):
    application_id: int
    key_id: int
    key_status: str
    returned_at: datetime


class KeyCheckoutResponse(BaseModel):
    application_id: int
    key_id: int
    key_status: str
    borrowed_at: datetime


class KeyResourceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    room_name: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, max_length=32)
