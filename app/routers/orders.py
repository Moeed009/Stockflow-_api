import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.order import OrderCreate, OrderResponse, OrderStatusUpdate
from app.services import order_service
from app.dependencies.auth import require_customer, require_business
from app.models.user import User


router = APIRouter(
    prefix="/orders",
    tags=["Orders"]
)


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create order(Customer)"
)
def create_order(
    data: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return order_service.create_order(
        db,
        current_user.id,
        data
    )


@router.get(
    "/my-orders",
    response_model=list[OrderResponse],
    summary="List my orders(Customer)"
)
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return order_service.list_customer_orders(
        db,
        current_user.id
    )


@router.get(
    "/my-order",
    response_model=OrderResponse,
    summary="Get my order (Customer)"
)
def get_my_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer)
):
    return order_service.get_customer_order(
        db,
        current_user.id,
        order_id
    )


@router.get(
    "",
    response_model=list[OrderResponse],
    summary="List all business orders (business)"
)
def list_all_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business)
):
    return order_service.list_all_orders_for_business(
        db,
        current_user.id
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status"
)
def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business)
):
    return order_service.update_order_status(
        db,
        current_user.id,
        order_id,
        data.status
    )