import uuid
from pydantic import BaseModel, EmailStr, Field, model_validator

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
   
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole

    full_name: str | None = None       
    business_name: str | None = None   

    @model_validator(mode="after")
    def validate_role_specific_fields(self):
       
        if self.role == UserRole.BUSINESS:
            if not self.business_name or not self.business_name.strip():
                raise ValueError("business_name is required when role is BUSINESS")
            self.full_name = None
        elif self.role == UserRole.CUSTOMER:
            self.business_name = None
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    full_name: str | None = None
    business_name: str | None = None

    model_config = {"from_attributes": True}