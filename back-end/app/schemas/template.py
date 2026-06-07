from pydantic import BaseModel


class ApplicationTemplateRead(BaseModel):
    id: str
    name: str
    application_type: str
    file_type: str
    download_url: str
