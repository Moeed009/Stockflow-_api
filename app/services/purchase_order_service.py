import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.purchase_order import PurchaseOrder, PurchaseOrderItem
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.supplier import Supplier
from app.models.enums import PurchaseOrderStatus
from app.schemas.purchase_order import PurchaseOrderCreate


def create_purchase_order(db: Session, business_id: uuid.UUID, data: PurchaseOrderCreate) -> PurchaseOrder:
    supplier = db.get(Supplier, data.supplier_id)
    if not supplier or supplier.business_id != business_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Supplier not found")

    po = PurchaseOrder(
        business_id=business_id,
        supplier_id=data.supplier_id,
        status=PurchaseOrderStatus.PENDING,
        total_amount=Decimal("0"),
    )
    db.add(po)
    db.flush()

    total = Decimal("0")
    for item in data.items:
        product = db.get(Product, item.product_id)
        if not product or product.business_id != business_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Product {item.product_id} not found")

        subtotal = item.unit_cost * item.quantity
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_cost=item.unit_cost,
            subtotal=subtotal,
        )
        db.add(po_item)
        total += subtotal

    po.total_amount = total
    db.commit()
    db.refresh(po)
    return po


def list_purchase_orders(db: Session, business_id: uuid.UUID) -> list[PurchaseOrder]:
    return db.query(PurchaseOrder).filter(PurchaseOrder.business_id == business_id).all()


def get_purchase_order_or_404(db: Session, business_id: uuid.UUID, po_id: uuid.UUID) -> PurchaseOrder:
    po = db.get(PurchaseOrder, po_id)
    if not po or po.business_id != business_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Purchase order not found")
    return po


def update_purchase_order_status(
    db: Session, business_id: uuid.UUID, po_id: uuid.UUID, new_status: PurchaseOrderStatus
) -> PurchaseOrder:
   
    po = get_purchase_order_or_404(db, business_id, po_id)

    if po.status == PurchaseOrderStatus.RECEIVED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,detail="Purchase order is already received" )
    if po.status == PurchaseOrderStatus.CANCELLED:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,detail="Cancelled purchase order cannot be updated" )

    if new_status == PurchaseOrderStatus.RECEIVED:
        for item in po.items:
            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == item.product_id)
                .with_for_update()
                .first()
            )
            if inventory:
                inventory.quantity += item.quantity

    po.status = new_status
    db.commit()
    db.refresh(po)
    return po
