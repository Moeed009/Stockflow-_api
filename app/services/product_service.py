import uuid

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.inventory import Inventory
from app.models.category import Category
from app.models.enums import ProductStatus
from app.schemas.product import ProductCreate, ProductUpdate


def _to_response_dict(product: Product) -> dict:
    
    return {
        "id": product.id,
        "business_id": product.business_id,
        "category_id": product.category_id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "status": product.status,
        "created_at": product.created_at,
        "available_quantity": product.inventory.quantity if product.inventory else 0,
    }


def create_product(db: Session, business_id: uuid.UUID, data: ProductCreate) -> dict:
    
    if db.query(Product).filter(Product.sku == data.sku).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "SKU already exists")

    if data.category_id is not None:
        category = db.get(Category, data.category_id)
        if category is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")

    product = Product(
        business_id=business_id,
        category_id=data.category_id,
        sku=data.sku,
        name=data.name,
        description=data.description,
        price=data.price,
    )

    try:
        db.add(product)
        db.flush()  

        inventory = Inventory(product_id=product.id, quantity=data.initial_quantity)
        db.add(inventory)

        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to create product. Please try again."
        )

    db.refresh(product)
    return _to_response_dict(product)


def list_products(db: Session, customer_view: bool = False) -> list[dict]:
    query = db.query(Product)
    if customer_view:
        query = query.filter(Product.status == ProductStatus.ACTIVE)
    return [_to_response_dict(p) for p in query.all()]


def get_product_or_404(db: Session, product_id: uuid.UUID) -> Product:
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Product not found")
    return product


def get_product_response(db: Session, product_id: uuid.UUID) -> dict:
    return _to_response_dict(get_product_or_404(db, product_id))


def update_product(db: Session, business_id: uuid.UUID, product_id: uuid.UUID, data: ProductUpdate) -> dict:
    product = get_product_or_404(db, product_id)
    if product.business_id != business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not own this product")

    update_data = data.model_dump(exclude_unset=True)

    if "category_id" in update_data and update_data["category_id"] is not None:
        category = db.get(Category, update_data["category_id"])
        if category is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")

    for field, value in update_data.items():
        setattr(product, field, value)

    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update product. Please try again."
        )

    db.refresh(product)
    return _to_response_dict(product)


def delete_product(db: Session, business_id: uuid.UUID, product_id: uuid.UUID) -> None:
    product = get_product_or_404(db, product_id)
    if product.business_id != business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not own this product")

    try:
        db.delete(product)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to delete product. Please try again."
        )