
import uuid

import pytest
from supabase_auth.errors import AuthApiError

from app.models.enums import UserRole
from tests.conftest import auth_header, make_access_token


def _auth_error(message="Simulated Supabase failure", status_code=400, code="bad_request"):
    return AuthApiError(message, status_code, code)



class TestRegistration:
    def test_register_customer_success(self, client, mock_supabase_admin):
        payload = {
            "email": "casey@example.com",
            "password": "supersecret1",
            "role": "CUSTOMER",
            "full_name": "Casey Customer",
        }
        resp = client.post("/Auth/register", json=payload)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["email"] == "casey@example.com"
        assert body["role"] == "CUSTOMER"
        assert body["full_name"] == "Casey Customer"
        assert body["business_name"] is None
        mock_supabase_admin.auth.admin.create_user.assert_called_once()

    def test_register_business_success(self, client, mock_supabase_admin):
        payload = {
            "email": "biz@example.com",
            "password": "supersecret1",
            "role": "BUSINESS",
            "business_name": "Acme Supplies",
        }
        resp = client.post("/Auth/register", json=payload)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["business_name"] == "Acme Supplies"
        assert body["full_name"] is None

    def test_register_business_without_business_name_fails_validation(self, client, mock_supabase_admin):
        payload = {"email": "biz2@example.com", "password": "supersecret1", "role": "BUSINESS"}
        resp = client.post("/Auth/register", json=payload)
        assert resp.status_code == 422
        mock_supabase_admin.auth.admin.create_user.assert_not_called()

    def test_register_password_too_short_fails_validation(self, client, mock_supabase_admin):
        payload = {"email": "short@example.com", "password": "short", "role": "CUSTOMER"}
        resp = client.post("/Auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_invalid_email_fails_validation(self, client, mock_supabase_admin):
        payload = {"email": "not-an-email", "password": "supersecret1", "role": "CUSTOMER"}
        resp = client.post("/Auth/register", json=payload)
        assert resp.status_code == 422

    def test_register_duplicate_local_email_rejected_before_hitting_supabase(
        self, client, mock_supabase_admin, customer
    ):
        payload = {
            "email": customer.email,
            "password": "supersecret1",
            "role": "CUSTOMER",
            "full_name": "Duplicate",
        }
        resp = client.post("/Auth/register", json=payload)
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()
        mock_supabase_admin.auth.admin.create_user.assert_not_called()

    def test_register_supabase_failure_surfaces_as_400(self, client, mock_supabase_admin):
        mock_supabase_admin.auth.admin.create_user.side_effect = _auth_error(
            "User already registered", 400, "user_exists"
        )
        payload = {
            "email": "willfail@example.com",
            "password": "supersecret1",
            "role": "CUSTOMER",
            "full_name": "Will Fail",
        }
        resp = client.post("/Auth/register", json=payload)
        assert resp.status_code == 400
        assert "registration failed" in resp.json()["detail"].lower()



class TestLogin:
    def test_login_success_returns_tokens(self, client, mock_supabase_anon):
        mock_supabase_anon.auth.sign_in_with_password.return_value.session.access_token = "access-123"
        mock_supabase_anon.auth.sign_in_with_password.return_value.session.refresh_token = "refresh-123"

        resp = client.post("/Auth/login", json={"email": "casey@example.com", "password": "supersecret1"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["access_token"] == "access-123"
        assert body["refresh_token"] == "refresh-123"
        assert body["token_type"] == "bearer"

    def test_login_invalid_credentials_returns_401(self, client, mock_supabase_anon):
        mock_supabase_anon.auth.sign_in_with_password.side_effect = _auth_error(
            "Invalid login credentials", 400, "invalid_credentials"
        )
        resp = client.post("/Auth/login", json={"email": "casey@example.com", "password": "wrong"})
        assert resp.status_code == 401
        assert "invalid email or password" in resp.json()["detail"].lower()

    def test_login_missing_fields_fails_validation(self, client, mock_supabase_anon):
        resp = client.post("/Auth/login", json={"email": "casey@example.com"})
        assert resp.status_code == 422



class TestRefresh:
    def test_refresh_returns_new_tokens(self, client, mock_supabase_anon):
        mock_supabase_anon.auth.refresh_session.return_value.session.access_token = "new-access"
        mock_supabase_anon.auth.refresh_session.return_value.session.refresh_token = "new-refresh"

        resp = client.post("/Auth/refresh", json={"refresh_token": "old-refresh"})
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["access_token"] == "new-access"
        assert body["refresh_token"] == "new-refresh"
        mock_supabase_anon.auth.refresh_session.assert_called_once_with("old-refresh")

    def test_refresh_rotates_tokens_on_each_call(self, client, mock_supabase_anon):
        from tests.conftest import _FakeAuthResult

        mock_supabase_anon.auth.refresh_session.side_effect = [
            _FakeAuthResult("access-1", "refresh-1"),
            _FakeAuthResult("access-2", "refresh-2"),
        ]

        first = client.post("/Auth/refresh", json={"refresh_token": "seed-token"})
        assert first.json()["refresh_token"] == "refresh-1"

        second = client.post("/Auth/refresh", json={"refresh_token": "refresh-1"})
        assert second.json()["refresh_token"] == "refresh-2"

        
        assert first.json()["access_token"] != second.json()["access_token"]
        assert mock_supabase_anon.auth.refresh_session.call_count == 2

    def test_refresh_invalid_token_returns_401(self, client, mock_supabase_anon):
        mock_supabase_anon.auth.refresh_session.side_effect = _auth_error(
            "Invalid Refresh Token", 401, "invalid_refresh_token"
        )
        resp = client.post("/Auth/refresh", json={"refresh_token": "garbage"})
        assert resp.status_code == 401
        assert "invalid or expired refresh token" in resp.json()["detail"].lower()



class TestLogout:
    def test_logout_revokes_session(self, client, mock_supabase_admin, customer_headers):
        resp = client.post("/Auth/logout", headers=customer_headers)
        assert resp.status_code == 204
        mock_supabase_admin.auth.admin.sign_out.assert_called_once()
        called_token = mock_supabase_admin.auth.admin.sign_out.call_args.args[0]
        assert called_token == customer_headers["Authorization"].split(" ", 1)[1]
        assert mock_supabase_admin.auth.admin.sign_out.call_args.kwargs.get("scope") == "global"

    def test_logout_without_token_is_rejected(self, client, mock_supabase_admin):
        resp = client.post("/Auth/logout")
        assert resp.status_code in (401, 403)

    def test_logout_tolerates_supabase_failure(self, client, mock_supabase_admin, customer_headers):
        mock_supabase_admin.auth.admin.sign_out.side_effect = _auth_error(
            "Token already revoked", 401, "already_revoked"
        )
        resp = client.post("/Auth/logout", headers=customer_headers)
        # logout swallows Supabase-side errors so the client always sees success
        assert resp.status_code == 204



class TestAccessTokenProtection:
    def test_protected_endpoint_without_token_is_rejected(self, client):
        resp = client.get("/me")
        assert resp.status_code in (401, 403)

    def test_protected_endpoint_with_garbage_token_is_401(self, client):
        resp = client.get("/me", headers={"Authorization": "Bearer not-a-real-jwt"})
        assert resp.status_code == 401

    def test_protected_endpoint_with_wrong_signature_is_401(self, client, customer):
        bad_token = make_access_token(customer.id, secret="totally-wrong-secret")
        resp = client.get("/me", headers={"Authorization": f"Bearer {bad_token}"})
        assert resp.status_code == 401

    def test_protected_endpoint_with_expired_token_is_401(self, client, customer):
        expired = make_access_token(customer.id, expired=True)
        resp = client.get("/me", headers={"Authorization": f"Bearer {expired}"})
        assert resp.status_code == 401

    def test_protected_endpoint_with_wrong_audience_is_401(self, client, customer):
        bad_aud = make_access_token(customer.id, audience="not-authenticated")
        resp = client.get("/me", headers={"Authorization": f"Bearer {bad_aud}"})
        assert resp.status_code == 401

    def test_protected_endpoint_for_unknown_user_id_is_401(self, client):
        token = make_access_token(uuid.uuid4())
        resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401

    def test_protected_endpoint_for_inactive_user_is_401(self, client, make_user):
        inactive = make_user(role=UserRole.CUSTOMER, is_active=False)
        resp = client.get("/me", headers=auth_header(inactive.id))
        assert resp.status_code == 401

    def test_protected_endpoint_with_valid_token_succeeds(self, client, customer_headers, customer):
        resp = client.get("/me", headers=customer_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == str(customer.id)



class TestRoleBasedAuthorization:
    def test_customer_cannot_access_business_only_endpoint(self, client, customer_headers):
        resp = client.post("/suppliers", json={"name": "Nope Inc"}, headers=customer_headers)
        assert resp.status_code == 403

    def test_business_cannot_access_customer_only_endpoint(self, client, business_headers):
        resp = client.get("/orders/my-orders", headers=business_headers)
        assert resp.status_code == 403

    def test_business_can_access_business_only_endpoint(self, client, business_headers):
        resp = client.get("/suppliers", headers=business_headers)
        assert resp.status_code == 200

    def test_customer_can_access_customer_only_endpoint(self, client, customer_headers):
        resp = client.get("/orders/my-orders", headers=customer_headers)
        assert resp.status_code == 200
