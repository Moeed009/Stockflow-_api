import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse
from app.services import product_service
from app.dependencies.auth import require_business, get_current_user
from app.models.user import User
from app.models.enums import UserRole

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    data: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    return product_service.create_product(db, current_user.id, data)


@router.get("/list_products", response_model=list[ProductResponse] , summary="Customer and business can see list_products ")
def list_products(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    customer_view = current_user.role == UserRole.CUSTOMER
    return product_service.list_products(db, customer_view=customer_view)


@router.get("/{product_id}", response_model=ProductResponse , summary="get_product (Customer and business can see)")
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)):
    return product_service.get_product_response(db, product_id)


@router.put("/{product_id}", response_model=ProductResponse , summary="update_product (Business only)")
def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
):
    return product_service.update_product(db, current_user.id, product_id, data)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT , summary=" delete_product(Business only)")
def delete_product(
    product_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    product_service.delete_product(db, current_user.id, product_id)