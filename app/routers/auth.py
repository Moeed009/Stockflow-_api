from fastapi import APIRouter, Depends, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from fastapi import APIRouter, Cookie, Depends, Response, status
from app.db.session import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UserPublic
from app.services import auth_service
from app.dependencies.auth import get_current_user, bearer_scheme
from app.models.user import User

router = APIRouter(prefix="/Auth", tags=["Authentication"])


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED, summary="Register a new user")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
   
    return auth_service.register(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest):
  
    return auth_service.login(data)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest):
    return auth_service.refresh_access_token(data.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    auth_service.logout(credentials.credentials)


