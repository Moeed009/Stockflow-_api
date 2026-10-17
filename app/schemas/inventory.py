import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class InventoryAdjustRequest(BaseModel):
    
    quantity_change: int  
    reason: str | None = None


class InventoryResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    updated_at: datetime

    model_config = {"from_attributes": True}
