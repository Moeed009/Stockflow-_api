import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.inventory import Inventory
from app.models.enums import OrderStatus, ProductStatus
from app.schemas.order import OrderCreate


def create_order(
    db: Session,
    customer_id: uuid.UUID,
    data: OrderCreate
) -> Order:
    order = Order(
        customer_id=customer_id,
        status=OrderStatus.PENDING,
        total_amount=Decimal("0")
    )

    db.add(order)
    db.flush()

    total = Decimal("0")

    try:
        for item in data.items:
            product = (
                db.query(Product)
                .filter(Product.id == item.product_id)
                .with_for_update()
                .first()
            )

            if not product or product.status != ProductStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {item.product_id} not available"
                )

            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == item.product_id)
                .with_for_update()
                .first()
            )

            if not inventory or inventory.quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Insufficient stock for product '{product.name}' "
                        f"(available: {inventory.quantity if inventory else 0}, "
                        f"requested: {item.quantity})"
                    )
                )

            inventory.quantity -= item.quantity

            subtotal = product.price * item.quantity

            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=item.quantity,
                unit_price=product.price,
                subtotal=subtotal
            )

            db.add(order_item)
            total += subtotal

        order.total_amount = total
        order.status = OrderStatus.CONFIRMED

        db.commit()
        db.refresh(order)

        return order

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


def list_customer_orders(
    db: Session,
    customer_id: uuid.UUID
) -> list[Order]:
    return (
        db.query(Order)
        .filter(Order.customer_id == customer_id)
        .order_by(Order.id.desc())
        .all()
    )


def get_order_or_404(
    db: Session,
    order_id: uuid.UUID
) -> Order:
    order = db.get(Order, order_id)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return order


def get_customer_order(
    db: Session,
    customer_id: uuid.UUID,
    order_id: uuid.UUID
) -> Order:
    order = get_order_or_404(db, order_id)

    if order.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not your order"
        )

    return order


def list_all_orders_for_business(
    db: Session,
    business_id: uuid.UUID) -> list[Order]:
    return (
        db.query(Order)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(Product.business_id == business_id)
        .distinct()
        .order_by(Order.id.desc())
        .all()
    )


def update_order_status(
    db: Session,
    business_id: uuid.UUID,
    order_id: uuid.UUID,
    new_status: OrderStatus
) -> Order:
    order = get_order_or_404(db, order_id)

    business_owns_order = (
        db.query(OrderItem)
        .join(Product, Product.id == OrderItem.product_id)
        .filter(
            OrderItem.order_id == order.id,
            Product.business_id == business_id
        )
        .first()
    )

    if not business_owns_order:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to update this order"
        )

    if order.status == OrderStatus.CANCELLED:
        if new_status != OrderStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change status of a cancelled order"
            )

        return order

    if new_status == OrderStatus.CANCELLED:
        for item in order.items:
            inventory = (
                db.query(Inventory)
                .filter(Inventory.product_id == item.product_id)
                .with_for_update()
                .first()
            )

            if inventory:
                inventory.quantity += item.quantity

    order.status = new_status

    try:
        db.commit()
        db.refresh(order)
        return order

    except Exception:
        db.rollback()
        raise