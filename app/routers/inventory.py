import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.inventory import InventoryAdjustRequest, InventoryResponse
from app.services import inventory_service
from app.dependencies.auth import require_business
from app.models.user import User

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("/{product_id}", response_model=InventoryResponse)
def get_inventory(product_id: uuid.UUID, db: Session = Depends(get_db),
     current_user: User = Depends(require_business),):
   
    return inventory_service.get_inventory_by_product(db, product_id)


@router.patch("/{product_id}/adjust", response_model=InventoryResponse)
def adjust_inventory(
    product_id: uuid.UUID,
    data: InventoryAdjustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
):
    return inventory_service.adjust_inventory(db, current_user.id, product_id, data)
