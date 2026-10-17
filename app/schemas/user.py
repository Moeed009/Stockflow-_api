from pydantic import BaseModel, EmailStr, Field


class UserUpdateRequest(BaseModel):
   
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8)
