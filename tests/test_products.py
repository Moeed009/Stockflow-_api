
import uuid


def _create_product(client, headers, sku="SKU-1", name="Widget", price="19.99",
                     initial_quantity=10, category_id=None, description=None):
    payload = {
        "sku": sku,
        "name": name,
        "price": price,
        "initial_quantity": initial_quantity,
    }
    if category_id is not None:
        payload["category_id"] = category_id
    if description is not None:
        payload["description"] = description
    return client.post("/products", json=payload, headers=headers)


class TestCreateProduct:
    def test_business_can_create_product_with_initial_stock(self, client, business_headers, business):
        resp = _create_product(client, business_headers, initial_quantity=25)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["business_id"] == str(business.id)
        assert body["available_quantity"] == 25
        assert body["status"] == "ACTIVE"

    def test_create_product_defaults_to_zero_stock_when_omitted(self, client, business_headers):
        resp = client.post(
            "/products",
            json={"sku": "SKU-DEFAULT", "name": "No Stock Item", "price": "5.00"},
            headers=business_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["available_quantity"] == 0

    def test_customer_cannot_create_product(self, client, customer_headers):
        resp = _create_product(client, customer_headers)
        assert resp.status_code == 403

    def test_duplicate_sku_rejected(self, client, business_headers):
        _create_product(client, business_headers, sku="DUP-1")
        resp = _create_product(client, business_headers, sku="DUP-1", name="Different Name")
        assert resp.status_code == 400
        assert "sku" in resp.json()["detail"].lower()

    def test_create_product_with_unknown_category_returns_404(self, client, business_headers):
        resp = _create_product(client, business_headers, category_id=str(uuid.uuid4()))
        assert resp.status_code == 404

    def test_create_product_with_valid_category(self, client, business_headers):
        category = client.post(
            "/categories", json={"name": "Toys"}, headers=business_headers
        ).json()
        resp = _create_product(client, business_headers, sku="SKU-CAT", category_id=category["id"])
        assert resp.status_code == 201
        assert resp.json()["category_id"] == category["id"]

    def test_price_must_be_positive(self, client, business_headers):
        resp = _create_product(client, business_headers, sku="SKU-NEG", price="0")
        assert resp.status_code == 422

    def test_negative_price_rejected(self, client, business_headers):
        resp = _create_product(client, business_headers, sku="SKU-NEG2", price="-5.00")
        assert resp.status_code == 422

    def test_blank_name_rejected(self, client, business_headers):
        resp = _create_product(client, business_headers, sku="SKU-BLANK", name="   ")
        assert resp.status_code == 422

    def test_blank_sku_rejected(self, client, business_headers):
        resp = _create_product(client, business_headers, sku="   ")
        assert resp.status_code == 422

    def test_negative_initial_quantity_rejected(self, client, business_headers):
        resp = _create_product(client, business_headers, sku="SKU-NEGQ", initial_quantity=-1)
        assert resp.status_code == 422


class TestListProducts:
    def test_business_sees_all_products_including_inactive(self, client, business_headers):
        active = _create_product(client, business_headers, sku="ACTIVE-1").json()
        inactive = _create_product(client, business_headers, sku="INACTIVE-1").json()
        client.put(f"/products/{inactive['id']}", json={"status": "INACTIVE"}, headers=business_headers)

        resp = client.get("/products/list_products", headers=business_headers)
        skus = {p["sku"] for p in resp.json()}
        assert "ACTIVE-1" in skus
        assert "INACTIVE-1" in skus

    def test_customer_only_sees_active_products(self, client, business_headers, customer_headers):
        active = _create_product(client, business_headers, sku="ACTIVE-2").json()
        inactive = _create_product(client, business_headers, sku="INACTIVE-2").json()
        client.put(f"/products/{inactive['id']}", json={"status": "INACTIVE"}, headers=business_headers)

        resp = client.get("/products/list_products", headers=customer_headers)
        skus = {p["sku"] for p in resp.json()}
        assert "ACTIVE-2" in skus
        assert "INACTIVE-2" not in skus

    def test_list_products_requires_auth(self, client):
        resp = client.get("/products/list_products")
        assert resp.status_code in (401, 403)


class TestGetProduct:
    def test_get_single_product_is_public(self, client, business_headers):
        created = _create_product(client, business_headers, sku="PUBLIC-1").json()
        resp = client.get(f"/products/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["sku"] == "PUBLIC-1"

    def test_get_missing_product_returns_404(self, client):
        resp = client.get(f"/products/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateProduct:
    def test_owner_can_update_product(self, client, business_headers):
        created = _create_product(client, business_headers, sku="UPD-1").json()
        resp = client.put(
            f"/products/{created['id']}", json={"price": "29.99", "name": "Updated"}, headers=business_headers
        )
        assert resp.status_code == 200
        assert resp.json()["price"] == "29.99"
        assert resp.json()["name"] == "Updated"

    def test_non_owner_cannot_update_product(self, client, business_headers, other_business_headers):
        created = _create_product(client, business_headers, sku="UPD-2").json()
        resp = client.put(
            f"/products/{created['id']}", json={"price": "1.00"}, headers=other_business_headers
        )
        assert resp.status_code == 403

    def test_customer_cannot_update_product(self, client, business_headers, customer_headers):
        created = _create_product(client, business_headers, sku="UPD-3").json()
        resp = client.put(
            f"/products/{created['id']}", json={"price": "1.00"}, headers=customer_headers
        )
        assert resp.status_code == 403

    def test_update_with_unknown_category_returns_404(self, client, business_headers):
        created = _create_product(client, business_headers, sku="UPD-4").json()
        resp = client.put(
            f"/products/{created['id']}", json={"category_id": str(uuid.uuid4())}, headers=business_headers
        )
        assert resp.status_code == 404


class TestDeleteProduct:
    def test_owner_can_delete_product(self, client, business_headers):
        created = _create_product(client, business_headers, sku="DEL-1").json()
        resp = client.delete(f"/products/{created['id']}", headers=business_headers)
        assert resp.status_code == 204
        assert client.get(f"/products/{created['id']}").status_code == 404

    def test_non_owner_cannot_delete_product(self, client, business_headers, other_business_headers):
        created = _create_product(client, business_headers, sku="DEL-2").json()
        resp = client.delete(f"/products/{created['id']}", headers=other_business_headers)
        assert resp.status_code == 403
