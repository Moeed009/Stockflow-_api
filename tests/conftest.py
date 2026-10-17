
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest


os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_ANON_KEY"] = "test-anon-key"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-role-key"
os.environ["SUPABASE_JWT_SECRET"] = "unit-test-super-secret-jwt-signing-key-1234567890"
os.environ["APP_NAME"] = "StockFlow API (test)"
os.environ["ENVIRONMENT"] = "test"

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]


from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "CHAR(32)"



from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.user import User  # noqa: E402


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _fresh_database():
    """Give every test function a clean schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture()
def db_session():
    
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
   
    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)



def make_access_token(user_id, *, expired=False, secret=None, audience="authenticated"):
    now = datetime.now(timezone.utc)
    exp = now - timedelta(minutes=5) if expired else now + timedelta(hours=1)
    claims = {
        "sub": str(user_id),
        "aud": audience,
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(claims, secret or SUPABASE_JWT_SECRET, algorithm="HS256")


def auth_header(user_id, **kwargs):
    return {"Authorization": f"Bearer {make_access_token(user_id, **kwargs)}"}


@pytest.fixture()
def make_user(db_session):
   

    def _make(role=UserRole.CUSTOMER, email=None, full_name="Test Customer",
              business_name=None, is_active=True):
        user = User(
            id=uuid.uuid4(),
            email=email or f"user-{uuid.uuid4().hex[:12]}@example.com",
            role=role,
            full_name=full_name if role == UserRole.CUSTOMER else None,
            business_name=(business_name or "Acme Supplies") if role == UserRole.BUSINESS else None,
            is_active=is_active,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture()
def customer(make_user):
    return make_user(role=UserRole.CUSTOMER, full_name="Casey Customer")


@pytest.fixture()
def business(make_user):
    return make_user(role=UserRole.BUSINESS, business_name="Acme Supplies")


@pytest.fixture()
def other_business(make_user):
    return make_user(role=UserRole.BUSINESS, business_name="Globex Corp")


@pytest.fixture()
def customer_headers(customer):
    return auth_header(customer.id)


@pytest.fixture()
def business_headers(business):
    return auth_header(business.id)


@pytest.fixture()
def other_business_headers(other_business):
    return auth_header(other_business.id)



class _FakeSupabaseUser:
    def __init__(self, user_id):
        self.id = user_id


class _FakeCreateUserResult:
    def __init__(self, user_id):
        self.user = _FakeSupabaseUser(user_id)


class _FakeSession:
    def __init__(self, access_token, refresh_token):
        self.access_token = access_token
        self.refresh_token = refresh_token


class _FakeAuthResult:
    def __init__(self, access_token="fake-access-token", refresh_token="fake-refresh-token"):
        self.session = _FakeSession(access_token, refresh_token)


@pytest.fixture()
def mock_supabase_admin(monkeypatch):
    """Patches the `supabase_admin` client used by auth_service + users router."""
    from unittest.mock import MagicMock

    import app.routers.users as users_router
    import app.services.auth_service as auth_service

    fake_admin = MagicMock()
    fake_admin.auth.admin.create_user.return_value = _FakeCreateUserResult(str(uuid.uuid4()))
    fake_admin.auth.admin.sign_out.return_value = None
    fake_admin.auth.admin.update_user_by_id.return_value = None

    monkeypatch.setattr(auth_service, "supabase_admin", fake_admin)
    monkeypatch.setattr(users_router, "supabase_admin", fake_admin)
    return fake_admin


@pytest.fixture()
def mock_supabase_anon(monkeypatch):
   
    from unittest.mock import MagicMock

    import app.services.auth_service as auth_service

    fake_anon = MagicMock()
    fake_anon.auth.sign_in_with_password.return_value = _FakeAuthResult()
    fake_anon.auth.refresh_session.return_value = _FakeAuthResult()

    monkeypatch.setattr(auth_service, "supabase_anon", fake_anon)
    return fake_anon
