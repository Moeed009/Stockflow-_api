


class TestGetMe:
    def test_customer_sees_own_profile(self, client, customer, customer_headers):
        resp = client.get("/me", headers=customer_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(customer.id)
        assert body["role"] == "CUSTOMER"
        assert body["full_name"] == customer.full_name

    def test_business_sees_own_profile(self, client, business, business_headers):
        resp = client.get("/me", headers=business_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["role"] == "BUSINESS"
        assert body["business_name"] == business.business_name

    def test_get_me_requires_auth(self, client):
        resp = client.get("/me")
        assert resp.status_code in (401, 403)


class TestUpdateMe:
    def test_update_full_name_persists(self, client, customer_headers, mock_supabase_admin):
        resp = client.patch("/me", json={"full_name": "New Name"}, headers=customer_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["full_name"] == "New Name"

    def test_update_email_triggers_supabase_update_and_local_update(
        self, client, customer, customer_headers, mock_supabase_admin
    ):
        resp = client.patch("/me", json={"email": "newmail@example.com"}, headers=customer_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["email"] == "newmail@example.com"
        mock_supabase_admin.auth.admin.update_user_by_id.assert_called_once()
        called_id, called_updates = mock_supabase_admin.auth.admin.update_user_by_id.call_args.args
        assert called_id == str(customer.id)
        assert called_updates == {"email": "newmail@example.com"}

    def test_update_password_only_goes_to_supabase_not_local_db(
        self, client, customer_headers, mock_supabase_admin
    ):
        resp = client.patch("/me", json={"password": "brandnewpassword"}, headers=customer_headers)
        assert resp.status_code == 200, resp.text
        mock_supabase_admin.auth.admin.update_user_by_id.assert_called_once()
        _, called_updates = mock_supabase_admin.auth.admin.update_user_by_id.call_args.args
        assert called_updates == {"password": "brandnewpassword"}

    def test_update_password_too_short_fails_validation(self, client, customer_headers, mock_supabase_admin):
        resp = client.patch("/me", json={"password": "short"}, headers=customer_headers)
        assert resp.status_code == 422
        mock_supabase_admin.auth.admin.update_user_by_id.assert_not_called()

    def test_update_me_requires_auth(self, client):
        resp = client.patch("/me", json={"full_name": "Nope"})
        assert resp.status_code in (401, 403)

    def test_partial_update_leaves_other_fields_untouched(
        self, client, customer, customer_headers, mock_supabase_admin
    ):
        resp = client.patch("/me", json={"full_name": "Only This Changes"}, headers=customer_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["full_name"] == "Only This Changes"
        assert body["email"] == customer.email
