import logging
import uuid
from fastapi import APIRouter, Cookie, Depends, Response, status
from fastapi import HTTPException, status
from supabase_auth.errors import AuthApiError
from sqlalchemy.orm import Session
from app.core.supabase_client import supabase_admin, supabase_anon
from app.models.user import User
from app.models.enums import UserRole
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse

logger = logging.getLogger(__name__)


def register(db: Session, data: RegisterRequest) -> User:
   
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email already registered")

    try:
        result = supabase_admin.auth.admin.create_user(
            {"email": data.email, "password": data.password ,  "email_confirm": True, "user_metadata": {
                    "role": data.role.value,
                    "full_name": data.full_name,
                    "business_name": data.business_name,
                },
            }
        )
    except AuthApiError as e:
        logger.warning(f"Supabase registration failed for {data.email}: {e.message}")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Registration failed: {e.message}")

    supabase_user_id = uuid.UUID(result.user.id)

    user = User(
        id=supabase_user_id,
        email=data.email,
        role=data.role,
        full_name=data.full_name if data.role == UserRole.CUSTOMER else None,
        business_name=data.business_name if data.role == UserRole.BUSINESS else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login(data: LoginRequest) -> TokenResponse:
    try:
        result = supabase_anon.auth.sign_in_with_password(
            {"email": data.email, "password": data.password}
        )
    except AuthApiError as e:
      
        logger.warning(f"Login failed for {data.email}: {e.message}")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    session = result.session
    return TokenResponse(access_token=session.access_token, refresh_token=session.refresh_token)


def login_form(email: str, password: str) -> TokenResponse:
   
    return login(LoginRequest(email=email, password=password))


def refresh_access_token(refresh_token: str) -> TokenResponse:
    try:
        result = supabase_anon.auth.refresh_session(refresh_token)
    except AuthApiError as e:
        print("REFRESH FAILED:", repr(e), "| token received:", repr(refresh_token))  
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")

    session = result.session
    return TokenResponse(access_token=session.access_token, refresh_token=session.refresh_token)


def logout(access_token: str) -> None:
    try: supabase_admin.auth.admin.sign_out(access_token, scope="global")
    except AuthApiError as e: logger.warning(f"Logout: Supabase sign_out failed (token may already be invalid): {e.message}")