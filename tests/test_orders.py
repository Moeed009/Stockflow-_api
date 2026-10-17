
import uuid


def _create_product(client, business_headers, sku="ORD-SKU", price="10.00", initial_quantity=10):
    resp = client.post(
        "/products",
        json={"sku": sku, "name": "Order Item", "price": price, "initial_quantity": initial_quantity},
        headers=business_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_order(client, customer_headers, items):
    return client.post("/orders", json={"items": items}, headers=customer_headers)


class TestCreateOrder:
    def test_customer_can_place_order_and_stock_decrements(self, client, business_headers, customer_headers):
        product = _create_product(client, business_headers, sku="ORD-1", price="10.00", initial_quantity=10)
        resp = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 3}])
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "CONFIRMED"
        assert body["total_amount"] == "30.00"
        assert len(body["items"]) == 1
        assert body["items"][0]["subtotal"] == "30.00"

        inventory = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert inventory["quantity"] == 7

    def test_order_total_sums_multiple_items(self, client, business_headers, customer_headers):
        p1 = _create_product(client, business_headers, sku="ORD-M1", price="5.00", initial_quantity=10)
        p2 = _create_product(client, business_headers, sku="ORD-M2", price="2.50", initial_quantity=10)
        resp = _create_order(
            client, customer_headers,
            [{"product_id": p1["id"], "quantity": 2}, {"product_id": p2["id"], "quantity": 4}],
        )
        assert resp.status_code == 201
        assert resp.json()["total_amount"] == "20.00"  # (2*5.00) + (4*2.50)

    def test_insufficient_stock_returns_400_and_leaves_inventory_untouched(
        self, client, business_headers, customer_headers
    ):
        product = _create_product(client, business_headers, sku="ORD-2", initial_quantity=3)
        resp = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 5}])
        assert resp.status_code == 400
        assert "insufficient stock" in resp.json()["detail"].lower()

        inventory = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert inventory["quantity"] == 3

    def test_failed_item_rolls_back_earlier_items_in_same_order(
        self, client, business_headers, customer_headers
    ):
        plenty = _create_product(client, business_headers, sku="ORD-ROLLBACK-A", initial_quantity=10)
        scarce = _create_product(client, business_headers, sku="ORD-ROLLBACK-B", initial_quantity=2)

        resp = _create_order(
            client, customer_headers,
            [
                {"product_id": plenty["id"], "quantity": 5},
                {"product_id": scarce["id"], "quantity": 5},
            ],
        )
        assert resp.status_code == 400

        plenty_inventory = client.get(f"/inventory/{plenty['id']}", headers=business_headers).json()
        assert plenty_inventory["quantity"] == 10  # rolled back, not partially decremented

        my_orders = client.get("/orders/my-orders", headers=customer_headers).json()
        assert my_orders == []

    def test_ordering_inactive_product_returns_404(self, client, business_headers, customer_headers):
        product = _create_product(client, business_headers, sku="ORD-3", initial_quantity=10)
        client.put(f"/products/{product['id']}", json={"status": "INACTIVE"}, headers=business_headers)

        resp = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 1}])
        assert resp.status_code == 404

    def test_ordering_nonexistent_product_returns_404(self, client, customer_headers):
        resp = _create_order(client, customer_headers, [{"product_id": str(uuid.uuid4()), "quantity": 1}])
        assert resp.status_code == 404

    def test_business_cannot_place_order(self, client, business_headers):
        resp = _create_order(client, business_headers, [{"product_id": str(uuid.uuid4()), "quantity": 1}])
        assert resp.status_code == 403

    def test_order_requires_at_least_one_item(self, client, customer_headers):
        resp = _create_order(client, customer_headers, [])
        assert resp.status_code == 422

    def test_order_item_quantity_must_be_positive(self, client, business_headers, customer_headers):
        product = _create_product(client, business_headers, sku="ORD-4")
        resp = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 0}])
        assert resp.status_code == 422


class TestListAndGetOrders:
    def test_customer_sees_only_their_own_orders(self, client, business_headers, customer_headers, make_user):
        from tests.conftest import auth_header
        from app.models.enums import UserRole

        product = _create_product(client, business_headers, sku="ORD-5", initial_quantity=10)
        _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 1}])

        other_customer = make_user(role=UserRole.CUSTOMER, full_name="Other Customer")
        other_headers = auth_header(other_customer.id)
        _create_order(client, other_headers, [{"product_id": product["id"], "quantity": 1}])

        resp = client.get("/orders/my-orders", headers=customer_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_customer_cannot_view_another_customers_order(
        self, client, business_headers, customer_headers, make_user
    ):
        from tests.conftest import auth_header
        from app.models.enums import UserRole

        product = _create_product(client, business_headers, sku="ORD-6", initial_quantity=10)
        order = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 1}]).json()

        other_customer = make_user(role=UserRole.CUSTOMER, full_name="Other Customer 2")
        other_headers = auth_header(other_customer.id)

        resp = client.get("/orders/my-order", params={"order_id": order["id"]}, headers=other_headers)
        assert resp.status_code == 403

    def test_get_missing_order_returns_404(self, client, customer_headers):
        resp = client.get("/orders/my-order", params={"order_id": str(uuid.uuid4())}, headers=customer_headers)
        assert resp.status_code == 404

    def test_business_lists_only_orders_containing_their_products(
        self, client, business_headers, other_business_headers, customer_headers
    ):
        mine = _create_product(client, business_headers, sku="ORD-7", initial_quantity=10)
        theirs = _create_product(client, other_business_headers, sku="ORD-8", initial_quantity=10)

        _create_order(client, customer_headers, [{"product_id": mine["id"], "quantity": 1}])
        _create_order(client, customer_headers, [{"product_id": theirs["id"], "quantity": 1}])

        resp = client.get("/orders", headers=business_headers)
        assert resp.status_code == 200
        products_in_orders = {item["product_id"] for order in resp.json() for item in order["items"]}
        assert mine["id"] in products_in_orders
        assert theirs["id"] not in products_in_orders

    def test_customer_cannot_list_all_business_orders(self, client, customer_headers):
        resp = client.get("/orders", headers=customer_headers)
        assert resp.status_code == 403


class TestOrderStatusUpdates:
    def test_business_can_update_status_of_order_containing_their_product(
        self, client, business_headers, customer_headers
    ):
        product = _create_product(client, business_headers, sku="ORD-9", initial_quantity=10)
        order = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 1}]).json()

        resp = client.patch(
            f"/orders/{order['id']}/status", json={"status": "COMPLETED"}, headers=business_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "COMPLETED"

    def test_unrelated_business_cannot_update_order_status(
        self, client, business_headers, other_business_headers, customer_headers
    ):
        product = _create_product(client, business_headers, sku="ORD-10", initial_quantity=10)
        order = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 1}]).json()

        resp = client.patch(
            f"/orders/{order['id']}/status", json={"status": "COMPLETED"}, headers=other_business_headers
        )
        assert resp.status_code == 403

    def test_customer_cannot_update_order_status(self, client, business_headers, customer_headers):
        product = _create_product(client, business_headers, sku="ORD-11", initial_quantity=10)
        order = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 1}]).json()

        resp = client.patch(
            f"/orders/{order['id']}/status", json={"status": "COMPLETED"}, headers=customer_headers
        )
        assert resp.status_code == 403

    def test_cancelling_order_restores_inventory(self, client, business_headers, customer_headers):
        product = _create_product(client, business_headers, sku="ORD-12", initial_quantity=10)
        order = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 4}]).json()

        after_order = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert after_order["quantity"] == 6

        resp = client.patch(
            f"/orders/{order['id']}/status", json={"status": "CANCELLED"}, headers=business_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"

        after_cancel = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert after_cancel["quantity"] == 10

    def test_cancelling_an_already_cancelled_order_is_idempotent(
        self, client, business_headers, customer_headers
    ):
        product = _create_product(client, business_headers, sku="ORD-13", initial_quantity=10)
        order = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 2}]).json()
        client.patch(f"/orders/{order['id']}/status", json={"status": "CANCELLED"}, headers=business_headers)

        resp = client.patch(
            f"/orders/{order['id']}/status", json={"status": "CANCELLED"}, headers=business_headers
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"

       
        inventory = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert inventory["quantity"] == 10

    def test_cancelled_order_cannot_move_to_another_status(
        self, client, business_headers, customer_headers
    ):
        product = _create_product(client, business_headers, sku="ORD-14", initial_quantity=10)
        order = _create_order(client, customer_headers, [{"product_id": product["id"], "quantity": 1}]).json()
        client.patch(f"/orders/{order['id']}/status", json={"status": "CANCELLED"}, headers=business_headers)

        resp = client.patch(
            f"/orders/{order['id']}/status", json={"status": "COMPLETED"}, headers=business_headers
        )
        assert resp.status_code == 400
        assert "cancelled" in resp.json()["detail"].lower()

    def test_update_status_for_missing_order_returns_404(self, client, business_headers):
        resp = client.patch(
            f"/orders/{uuid.uuid4()}/status", json={"status": "COMPLETED"}, headers=business_headers
        )
        assert resp.status_code == 404
