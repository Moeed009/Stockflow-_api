import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator

from app.models.enums import ProductStatus


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(gt=0, description="Price must be greater than 0")
    category_id: uuid.UUID | None = None
    initial_quantity: int = Field(default=0, ge=0, description="Starting stock quantity")

    @field_validator("sku", "name")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("cannot be empty or whitespace")
        return v


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal | None = Field(default=None, gt=0)
    category_id: uuid.UUID | None = None
    status: ProductStatus | None = None
    

class ProductResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    category_id: uuid.UUID | None
    sku: str
    name: str
    description: str | None
    price: Decimal
    status: ProductStatus
    created_at: datetime
    available_quantity: int = 0

    model_config = {"from_attributes": True}