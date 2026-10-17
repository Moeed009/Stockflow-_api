import uuid
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


def create_category(db: Session, business_id: uuid.UUID, data: CategoryCreate) -> Category:
    category = Category(**data.model_dump(), business_id=business_id)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def list_categories(db: Session) -> list[Category]:
    return db.query(Category).all()


def get_category_or_404(db: Session, category_id: uuid.UUID) -> Category:
    category = db.get(Category, category_id)
    if not category:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Category not found")
    return category


def update_category(db: Session, business_id: uuid.UUID, category_id: uuid.UUID, data: CategoryUpdate) -> Category:
    category = get_category_or_404(db, category_id)
    if category.business_id != business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your category")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, business_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = get_category_or_404(db, category_id)
    if category.business_id != business_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your category")
    db.delete(category)
    db.commit()
