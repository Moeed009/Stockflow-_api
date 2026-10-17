import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product
from app.schemas.inventory import InventoryAdjustRequest


def get_inventory_by_product(db: Session, product_id: uuid.UUID) -> Inventory:
    inventory = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    if not inventory:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Inventory record not found")
    return inventory


def adjust_inventory(
    db: Session, business_id: uuid.UUID, product_id: uuid.UUID, data: InventoryAdjustRequest) -> Inventory:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    if product.business_id != business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your product")

    inventory = get_inventory_by_product(db, product_id)
    new_quantity = inventory.quantity + data.quantity_change
    if new_quantity < 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adjustment would result in negative stock")

    inventory.quantity = new_quantity
    db.commit()
    db.refresh(inventory)
    return inventory
