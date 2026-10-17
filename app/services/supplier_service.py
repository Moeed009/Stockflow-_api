import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.schemas.supplier import SupplierCreate, SupplierUpdate


def create_supplier(db: Session, business_id: uuid.UUID, data: SupplierCreate) -> Supplier:
    supplier = Supplier(**data.model_dump(), business_id=business_id)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def list_suppliers(db: Session, business_id: uuid.UUID) -> list[Supplier]:
    return db.query(Supplier).filter(Supplier.business_id == business_id).all()


def get_supplier_or_404(db: Session, business_id: uuid.UUID, supplier_id: uuid.UUID) -> Supplier:
    supplier = db.get(Supplier, supplier_id)
    if not supplier or supplier.business_id != business_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")
    return supplier


def update_supplier(db: Session, business_id: uuid.UUID, supplier_id: uuid.UUID, data: SupplierUpdate) -> Supplier:
    supplier = get_supplier_or_404(db, business_id, supplier_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


def delete_supplier(db: Session, business_id: uuid.UUID, supplier_id: uuid.UUID) -> None:
    supplier = get_supplier_or_404(db, business_id, supplier_id)
    db.delete(supplier)
    db.commit()
