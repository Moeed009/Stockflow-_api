
import uuid


def _create_supplier(client, headers, name="Acme Wholesale"):
    return client.post("/suppliers", json={"name": name}, headers=headers).json()


def _create_product(client, headers, sku="PO-SKU", initial_quantity=0):
    resp = client.post(
        "/products",
        json={"sku": sku, "name": "PO Item", "price": "10.00", "initial_quantity": initial_quantity},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_po(client, headers, supplier_id, items):
    return client.post(
        "/purchase-orders", json={"supplier_id": supplier_id, "items": items}, headers=headers
    )


class TestCreatePurchaseOrder:
    def test_business_can_create_purchase_order_with_correct_total(self, client, business_headers, business):
        supplier = _create_supplier(client, business_headers)
        product = _create_product(client, business_headers, sku="PO-1")
        items = [{"product_id": product["id"], "quantity": 10, "unit_cost": "4.50"}]

        resp = _create_po(client, business_headers, supplier["id"], items)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "PENDING"
        assert body["total_amount"] == "45.00"
        assert len(body["items"]) == 1
        assert body["items"][0]["subtotal"] == "45.00"

    def test_total_sums_multiple_line_items(self, client, business_headers):
        supplier = _create_supplier(client, business_headers)
        p1 = _create_product(client, business_headers, sku="PO-MULTI-1")
        p2 = _create_product(client, business_headers, sku="PO-MULTI-2")
        items = [
            {"product_id": p1["id"], "quantity": 3, "unit_cost": "2.00"},
            {"product_id": p2["id"], "quantity": 5, "unit_cost": "1.50"},
        ]
        resp = _create_po(client, business_headers, supplier["id"], items)
        assert resp.status_code == 201
        assert resp.json()["total_amount"] == "13.50"

    def test_create_po_with_unowned_supplier_returns_404(
        self, client, business_headers, other_business_headers
    ):
        supplier = _create_supplier(client, other_business_headers)
        product = _create_product(client, business_headers, sku="PO-2")
        resp = _create_po(
            client, business_headers, supplier["id"],
            [{"product_id": product["id"], "quantity": 1, "unit_cost": "1.00"}],
        )
        assert resp.status_code == 404

    def test_create_po_with_unowned_product_returns_404(
        self, client, business_headers, other_business_headers
    ):
        supplier = _create_supplier(client, business_headers)
        other_product = _create_product(client, other_business_headers, sku="PO-3")
        resp = _create_po(
            client, business_headers, supplier["id"],
            [{"product_id": other_product["id"], "quantity": 1, "unit_cost": "1.00"}],
        )
        assert resp.status_code == 404

    def test_create_po_with_nonexistent_product_returns_404(self, client, business_headers):
        supplier = _create_supplier(client, business_headers)
        resp = _create_po(
            client, business_headers, supplier["id"],
            [{"product_id": str(uuid.uuid4()), "quantity": 1, "unit_cost": "1.00"}],
        )
        assert resp.status_code == 404

    def test_create_po_with_nonexistent_supplier_returns_404(self, client, business_headers):
        product = _create_product(client, business_headers, sku="PO-4")
        resp = _create_po(
            client, business_headers, str(uuid.uuid4()),
            [{"product_id": product["id"], "quantity": 1, "unit_cost": "1.00"}],
        )
        assert resp.status_code == 404

    def test_customer_cannot_create_purchase_order(self, client, customer_headers):
        resp = _create_po(client, customer_headers, str(uuid.uuid4()), [])
        assert resp.status_code == 403

    def test_po_requires_at_least_one_item(self, client, business_headers):
        supplier = _create_supplier(client, business_headers)
        resp = _create_po(client, business_headers, supplier["id"], [])
        assert resp.status_code == 422

    def test_po_item_quantity_must_be_positive(self, client, business_headers):
        supplier = _create_supplier(client, business_headers)
        product = _create_product(client, business_headers, sku="PO-5")
        resp = _create_po(
            client, business_headers, supplier["id"],
            [{"product_id": product["id"], "quantity": 0, "unit_cost": "1.00"}],
        )
        assert resp.status_code == 422

    def test_po_item_unit_cost_must_be_positive(self, client, business_headers):
        supplier = _create_supplier(client, business_headers)
        product = _create_product(client, business_headers, sku="PO-6")
        resp = _create_po(
            client, business_headers, supplier["id"],
            [{"product_id": product["id"], "quantity": 1, "unit_cost": "0"}],
        )
        assert resp.status_code == 422


class TestListAndGetPurchaseOrder:
    def test_list_purchase_orders_scoped_to_business(
        self, client, business_headers, other_business_headers
    ):
        supplier = _create_supplier(client, business_headers)
        product = _create_product(client, business_headers, sku="PO-LIST-1")
        _create_po(client, business_headers, supplier["id"],
                   [{"product_id": product["id"], "quantity": 1, "unit_cost": "1.00"}])

        other_supplier = _create_supplier(client, other_business_headers)
        other_product = _create_product(client, other_business_headers, sku="PO-LIST-2")
        _create_po(client, other_business_headers, other_supplier["id"],
                   [{"product_id": other_product["id"], "quantity": 1, "unit_cost": "1.00"}])

        resp = client.get("/purchase-orders", headers=business_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_other_businesses_po_returns_404(
        self, client, business_headers, other_business_headers
    ):
        supplier = _create_supplier(client, business_headers)
        product = _create_product(client, business_headers, sku="PO-GET-1")
        po = _create_po(client, business_headers, supplier["id"],
                         [{"product_id": product["id"], "quantity": 1, "unit_cost": "1.00"}]).json()

        resp = client.get(f"/purchase-orders/{po['id']}", headers=other_business_headers)
        assert resp.status_code == 404


class TestPurchaseOrderStatusTransitions:
    def _make_po(self, client, business_headers, quantity=20, initial_stock=0):
        supplier = _create_supplier(client, business_headers)
        product = _create_product(client, business_headers, sku=f"PO-STOCK-{uuid.uuid4().hex[:6]}",
                                   initial_quantity=initial_stock)
        po = _create_po(
            client, business_headers, supplier["id"],
            [{"product_id": product["id"], "quantity": quantity, "unit_cost": "2.00"}],
        ).json()
        return po, product

    def test_marking_received_increases_inventory(self, client, business_headers):
        po, product = self._make_po(client, business_headers, quantity=20, initial_stock=5)

        resp = client.patch(
            f"/purchase-orders/{po['id']}/status", json={"status": "RECEIVED"}, headers=business_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "RECEIVED"

        inventory = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert inventory["quantity"] == 25

    def test_ordered_status_does_not_touch_inventory(self, client, business_headers):
        po, product = self._make_po(client, business_headers, quantity=20, initial_stock=5)

        resp = client.patch(
            f"/purchase-orders/{po['id']}/status", json={"status": "ORDERED"}, headers=business_headers
        )
        assert resp.status_code == 200
        inventory = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert inventory["quantity"] == 5

    def test_received_po_cannot_be_changed_again(self, client, business_headers):
        po, product = self._make_po(client, business_headers, quantity=5, initial_stock=0)
        client.patch(f"/purchase-orders/{po['id']}/status", json={"status": "RECEIVED"}, headers=business_headers)

        resp = client.patch(
            f"/purchase-orders/{po['id']}/status", json={"status": "CANCELLED"}, headers=business_headers
        )
        assert resp.status_code == 400
        assert "already received" in resp.json()["detail"].lower()

    def test_cancelled_po_cannot_be_changed(self, client, business_headers):
        po, product = self._make_po(client, business_headers, quantity=5, initial_stock=0)
        client.patch(f"/purchase-orders/{po['id']}/status", json={"status": "CANCELLED"}, headers=business_headers)

        resp = client.patch(
            f"/purchase-orders/{po['id']}/status", json={"status": "ORDERED"}, headers=business_headers
        )
        assert resp.status_code == 400
        assert "cancelled" in resp.json()["detail"].lower()

    def test_non_owner_cannot_update_po_status(self, client, business_headers, other_business_headers):
        po, product = self._make_po(client, business_headers)
        resp = client.patch(
            f"/purchase-orders/{po['id']}/status", json={"status": "RECEIVED"}, headers=other_business_headers
        )
        assert resp.status_code == 404
