import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class SupplierCreate(BaseModel):
    name: str
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = None
    contact_email: EmailStr | None = None
    contact_phone: str | None = None
    address: str | None = None


class SupplierResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    name: str
    contact_email: str | None
    contact_phone: str | None
    address: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
