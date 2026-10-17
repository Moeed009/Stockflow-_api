
import uuid


def _create_category(client, headers, name="Electronics", description="Gadgets"):
    return client.post("/categories", json={"name": name, "description": description}, headers=headers)


class TestCreateCategory:
    def test_business_can_create_category(self, client, business_headers, business):
        resp = _create_category(client, business_headers)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["name"] == "Electronics"
        assert body["business_id"] == str(business.id)

    def test_customer_cannot_create_category(self, client, customer_headers):
        resp = _create_category(client, customer_headers)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_category(self, client):
        resp = client.post("/categories", json={"name": "Electronics"})
        assert resp.status_code in (401, 403)

    def test_create_category_missing_name_fails_validation(self, client, business_headers):
        resp = client.post("/categories", json={"description": "no name"}, headers=business_headers)
        assert resp.status_code == 422


class TestReadCategory:
    def test_list_categories_is_public(self, client, business_headers):
        _create_category(client, business_headers, name="Books")
        resp = client.get("/categories")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert "Books" in names

    def test_get_category_is_public(self, client, business_headers):
        created = _create_category(client, business_headers).json()
        resp = client.get(f"/categories/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["id"] == created["id"]

    def test_get_missing_category_returns_404(self, client):
        resp = client.get(f"/categories/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateCategory:
    def test_owner_can_update_category(self, client, business_headers):
        created = _create_category(client, business_headers).json()
        resp = client.put(
            f"/categories/{created['id']}", json={"name": "Renamed"}, headers=business_headers
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

    def test_non_owner_business_cannot_update_category(
        self, client, business_headers, other_business_headers
    ):
        created = _create_category(client, business_headers).json()
        resp = client.put(
            f"/categories/{created['id']}", json={"name": "Hijacked"}, headers=other_business_headers
        )
        assert resp.status_code == 403

    def test_customer_cannot_update_category(self, client, business_headers, customer_headers):
        created = _create_category(client, business_headers).json()
        resp = client.put(
            f"/categories/{created['id']}", json={"name": "Nope"}, headers=customer_headers
        )
        assert resp.status_code == 403

    def test_update_missing_category_returns_404(self, client, business_headers):
        resp = client.put(
            f"/categories/{uuid.uuid4()}", json={"name": "Ghost"}, headers=business_headers
        )
        assert resp.status_code == 404


class TestDeleteCategory:
    def test_owner_can_delete_category(self, client, business_headers):
        created = _create_category(client, business_headers).json()
        resp = client.delete(f"/categories/{created['id']}", headers=business_headers)
        assert resp.status_code == 204
        assert client.get(f"/categories/{created['id']}").status_code == 404

    def test_non_owner_business_cannot_delete_category(
        self, client, business_headers, other_business_headers
    ):
        created = _create_category(client, business_headers).json()
        resp = client.delete(f"/categories/{created['id']}", headers=other_business_headers)
        assert resp.status_code == 403
        assert client.get(f"/categories/{created['id']}").status_code == 200
