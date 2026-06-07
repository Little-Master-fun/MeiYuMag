from datetime import datetime

from pydantic import BaseModel


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

