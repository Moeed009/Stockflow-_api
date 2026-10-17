import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.services import category_service
from app.dependencies.auth import require_business
from app.models.user import User

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED , summary="Create a new category (Business users only)" )
def create_category(
    data: CategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(require_business)
):
    return category_service.create_category(db, current_user.id, data)


@router.get("", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return category_service.list_categories(db)


@router.get("/{category_id}", response_model=CategoryResponse , summary=" Get category " )
def get_category(category_id: uuid.UUID, db: Session = Depends(get_db)):
    return category_service.get_category_or_404(db, category_id)


@router.put("/{category_id}", response_model=CategoryResponse , summary=" update category (Business users only)")
def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business),
):
    return category_service.update_category(db, current_user.id, category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT , summary=" delete category (Business users only)")
def delete_category(
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_business)
):
    category_service.delete_category(db,current_user.id,category_id)

   