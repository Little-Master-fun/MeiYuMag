from pydantic import BaseModel, Field


class SduerInfo(BaseModel):
    sduid: str = Field(validation_alias="ID_NUMBER", description="学号")
    name: str = Field(validation_alias="USER_NAME", description="姓名")
    sex: str | None = Field(default=None, validation_alias="USER_SEX", description="性别")
    type: str | None = Field(default=None, validation_alias="ID_TYPE", description="人员类型")
    email: str | None = Field(default=None, validation_alias="EMAIL", description="邮箱")
    school: str | None = Field(default=None, validation_alias="UNIT_NAME", description="学院")
    tel: str | None = Field(default=None, validation_alias="MOBILE", description="电话")


class SduAuthResponse(BaseModel):
    message: str
    profile: SduerInfo
    is_sdu_verified: bool
