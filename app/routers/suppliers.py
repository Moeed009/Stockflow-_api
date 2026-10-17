import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.supplier import SupplierCreate, SupplierUpdate, SupplierResponse
from app.services import supplier_service
from app.dependencies.auth import require_business
from app.models.user import User

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.post("", response_model=SupplierResponse, status_code=status.HTTP_201_CREATED, summary="create_supplier (Business only)")
def create_supplier(
    data: SupplierCreate, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    return supplier_service.create_supplier(db, current_user.id, data)


@router.get("", response_model=list[SupplierResponse] , summary="list_suppliers (Business only)")
def list_suppliers(db: Session = Depends(get_db), current_user: User = Depends(require_business)):
    return supplier_service.list_suppliers(db, current_user.id)


@router.get("/{supplier_id}", response_model=SupplierResponse , summary="get_supplier (Business only)")
def get_supplier(
    supplier_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    return supplier_service.get_supplier_or_404(db, current_user.id, supplier_id)


@router.put("/{supplier_id}", response_model=SupplierResponse , summary="update_supplier (Business only)")
def update_supplier(
    supplier_id: uuid.UUID,
    data: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
):
    return supplier_service.update_supplier(db, current_user.id, supplier_id, data)


@router.delete("/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT , summary="delete_supplier (Business only)")
def delete_supplier(
    supplier_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    supplier_service.delete_supplier(db, current_user.id, supplier_id)
