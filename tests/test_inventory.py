
import uuid


def _create_product(client, headers, sku="INV-SKU", initial_quantity=10):
    resp = client.post(
        "/products",
        json={"sku": sku, "name": "Inventory Item", "price": "9.99", "initial_quantity": initial_quantity},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestGetInventory:
    def test_owner_can_view_inventory(self, client, business_headers):
        product = _create_product(client, business_headers, initial_quantity=15)
        resp = client.get(f"/inventory/{product['id']}", headers=business_headers)
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 15

    def test_customer_cannot_view_inventory(self, client, business_headers, customer_headers):
        product = _create_product(client, business_headers)
        resp = client.get(f"/inventory/{product['id']}", headers=customer_headers)
        assert resp.status_code == 403

    def test_unauthenticated_cannot_view_inventory(self, client, business_headers):
        product = _create_product(client, business_headers)
        resp = client.get(f"/inventory/{product['id']}")
        assert resp.status_code in (401, 403)

    def test_missing_product_inventory_returns_404(self, client, business_headers):
        resp = client.get(f"/inventory/{uuid.uuid4()}", headers=business_headers)
        assert resp.status_code == 404


class TestAdjustInventory:
    def test_owner_can_increase_stock(self, client, business_headers):
        product = _create_product(client, business_headers, initial_quantity=10)
        resp = client.patch(
            f"/inventory/{product['id']}/adjust",
            json={"quantity_change": 5, "reason": "restock"},
            headers=business_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 15

    def test_owner_can_decrease_stock(self, client, business_headers):
        product = _create_product(client, business_headers, initial_quantity=10)
        resp = client.patch(
            f"/inventory/{product['id']}/adjust",
            json={"quantity_change": -4},
            headers=business_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 6

    def test_adjustment_cannot_go_negative(self, client, business_headers):
        product = _create_product(client, business_headers, initial_quantity=5)
        resp = client.patch(
            f"/inventory/{product['id']}/adjust",
            json={"quantity_change": -10},
            headers=business_headers,
        )
        assert resp.status_code == 400
        assert "negative" in resp.json()["detail"].lower()

        
        check = client.get(f"/inventory/{product['id']}", headers=business_headers)
        assert check.json()["quantity"] == 5

    def test_adjustment_to_exactly_zero_is_allowed(self, client, business_headers):
        product = _create_product(client, business_headers, initial_quantity=5)
        resp = client.patch(
            f"/inventory/{product['id']}/adjust",
            json={"quantity_change": -5},
            headers=business_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["quantity"] == 0

    def test_non_owner_cannot_adjust_inventory(self, client, business_headers, other_business_headers):
        product = _create_product(client, business_headers, initial_quantity=10)
        resp = client.patch(
            f"/inventory/{product['id']}/adjust",
            json={"quantity_change": 5},
            headers=other_business_headers,
        )
        assert resp.status_code == 403

    def test_customer_cannot_adjust_inventory(self, client, business_headers, customer_headers):
        product = _create_product(client, business_headers)
        resp = client.patch(
            f"/inventory/{product['id']}/adjust",
            json={"quantity_change": 1},
            headers=customer_headers,
        )
        assert resp.status_code == 403

    def test_adjust_missing_product_returns_404(self, client, business_headers):
        resp = client.patch(
            f"/inventory/{uuid.uuid4()}/adjust",
            json={"quantity_change": 1},
            headers=business_headers,
        )
        assert resp.status_code == 404
