
import uuid


def _create_supplier(client, headers, name="Global Parts", contact_email="sales@globalparts.example"):
    return client.post(
        "/suppliers", json={"name": name, "contact_email": contact_email}, headers=headers
    )


class TestCreateSupplier:
    def test_business_can_create_supplier(self, client, business_headers, business):
        resp = _create_supplier(client, business_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Global Parts"
        assert body["business_id"] == str(business.id)

    def test_customer_cannot_create_supplier(self, client, customer_headers):
        resp = _create_supplier(client, customer_headers)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_supplier(self, client):
        resp = client.post("/suppliers", json={"name": "Ghost Co"})
        assert resp.status_code in (401, 403)

    def test_invalid_contact_email_fails_validation(self, client, business_headers):
        resp = client.post(
            "/suppliers", json={"name": "Bad Email Co", "contact_email": "not-an-email"},
            headers=business_headers,
        )
        assert resp.status_code == 422

    def test_missing_name_fails_validation(self, client, business_headers):
        resp = client.post("/suppliers", json={"contact_email": "a@b.com"}, headers=business_headers)
        assert resp.status_code == 422


class TestListAndGetSupplier:
    def test_list_suppliers_is_scoped_to_business(
        self, client, business_headers, other_business_headers
    ):
        _create_supplier(client, business_headers, name="Mine")
        _create_supplier(client, other_business_headers, name="Theirs")

        resp = client.get("/suppliers", headers=business_headers)
        names = [s["name"] for s in resp.json()]
        assert "Mine" in names
        assert "Theirs" not in names

    def test_get_own_supplier_succeeds(self, client, business_headers):
        created = _create_supplier(client, business_headers).json()
        resp = client.get(f"/suppliers/{created['id']}", headers=business_headers)
        assert resp.status_code == 200

    def test_get_other_businesses_supplier_returns_404(
        self, client, business_headers, other_business_headers
    ):
        created = _create_supplier(client, business_headers).json()
        resp = client.get(f"/suppliers/{created['id']}", headers=other_business_headers)
        assert resp.status_code == 404

    def test_list_suppliers_requires_business_role(self, client, customer_headers):
        resp = client.get("/suppliers", headers=customer_headers)
        assert resp.status_code == 403


class TestUpdateSupplier:
    def test_owner_can_update_supplier(self, client, business_headers):
        created = _create_supplier(client, business_headers).json()
        resp = client.put(
            f"/suppliers/{created['id']}", json={"name": "Renamed Supplier"}, headers=business_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed Supplier"

    def test_other_business_cannot_update_supplier(
        self, client, business_headers, other_business_headers
    ):
        created = _create_supplier(client, business_headers).json()
        resp = client.put(
            f"/suppliers/{created['id']}", json={"name": "Hijacked"}, headers=other_business_headers
        )
        assert resp.status_code == 404

    def test_update_missing_supplier_returns_404(self, client, business_headers):
        resp = client.put(
            f"/suppliers/{uuid.uuid4()}", json={"name": "Ghost"}, headers=business_headers
        )
        assert resp.status_code == 404


class TestDeleteSupplier:
    def test_owner_can_delete_supplier(self, client, business_headers):
        created = _create_supplier(client, business_headers).json()
        resp = client.delete(f"/suppliers/{created['id']}", headers=business_headers)
        assert resp.status_code == 204
        assert client.get(f"/suppliers/{created['id']}", headers=business_headers).status_code == 404

    def test_other_business_cannot_delete_supplier(
        self, client, business_headers, other_business_headers
    ):
        created = _create_supplier(client, business_headers).json()
        resp = client.delete(f"/suppliers/{created['id']}", headers=other_business_headers)
        assert resp.status_code == 404
