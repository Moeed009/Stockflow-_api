import uuid
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field

from app.models.enums import PurchaseOrderStatus


class PurchaseOrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    unit_cost: Decimal = Field(gt=0)


class PurchaseOrderCreate(BaseModel):
    supplier_id: uuid.UUID
    items: list[PurchaseOrderItemCreate] = Field(min_length=1)


class PurchaseOrderItemResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    unit_cost: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class PurchaseOrderResponse(BaseModel):
    id: uuid.UUID
    business_id: uuid.UUID
    supplier_id: uuid.UUID
    status: PurchaseOrderStatus
    total_amount: Decimal
    created_at: datetime
    items: list[PurchaseOrderItemResponse] = []

    model_config = {"from_attributes": True}


class PurchaseOrderStatusUpdate(BaseModel):
    status: PurchaseOrderStatus
