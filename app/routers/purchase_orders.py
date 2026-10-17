import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.purchase_order import PurchaseOrderCreate, PurchaseOrderResponse, PurchaseOrderStatusUpdate
from app.services import purchase_order_service
from app.dependencies.auth import require_business
from app.models.user import User

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])


@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED , summary=" create_purchase_order (Business only)")
def create_purchase_order(
    data: PurchaseOrderCreate, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    return purchase_order_service.create_purchase_order(db, current_user.id, data)


@router.get("", response_model=list[PurchaseOrderResponse], summary=" list_purchase_orders (Business only)")
def list_purchase_orders(db: Session = Depends(get_db), current_user: User = Depends(require_business)):
    return purchase_order_service.list_purchase_orders(db, current_user.id)


@router.get("/{po_id}", response_model=PurchaseOrderResponse, summary="get_purchase_order (Business only)")
def get_purchase_order(
    po_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    return purchase_order_service.get_purchase_order_or_404(db, current_user.id, po_id)


@router.patch("/{po_id}/status", response_model=PurchaseOrderResponse, summary=" update_purchase_order_status (Business only)")
def update_purchase_order_status(
    po_id: uuid.UUID,
    data: PurchaseOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
):
    return purchase_order_service.update_purchase_order_status(db, current_user.id, po_id, data.status)
