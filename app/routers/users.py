from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.user import UserUpdateRequest
from app.schemas.auth import UserPublic
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.core.supabase_client import supabase_admin

router = APIRouter(prefix="", tags=["Users"])


@router.patch("/me", response_model=UserPublic)
def update_me(
    data: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    ):
    
    update_data = data.model_dump(exclude_unset=True)

    
    supabase_updates = {}
    if "password" in update_data:
        supabase_updates["password"] = update_data.pop("password")
    if "email" in update_data:
        supabase_updates["email"] = update_data["email"]
    if supabase_updates:
        supabase_admin.auth.admin.update_user_by_id(str(current_user.id), supabase_updates)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me", response_model=UserPublic)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user