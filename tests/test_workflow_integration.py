
import uuid

from app.models.enums import UserRole
from tests.conftest import auth_header


def _register_and_login(client, mock_supabase_admin, mock_supabase_anon, *, role, **extra):
    user_id = str(uuid.uuid4())
    mock_supabase_admin.auth.admin.create_user.return_value.user.id = user_id
    email = f"{role.lower()}-{uuid.uuid4().hex[:8]}@example.com"

    payload = {"email": email, "password": "supersecret1", "role": role, **extra}
    register_resp = client.post("/Auth/register", json=payload)
    assert register_resp.status_code == 201, register_resp.text

    return auth_header(uuid.UUID(user_id))


class TestFullInventoryAndOrderLifecycle:
    def test_supplier_to_customer_workflow(self, client, mock_supabase_admin, mock_supabase_anon):
        business_headers = _register_and_login(
            client, mock_supabase_admin, mock_supabase_anon, role="BUSINESS", business_name="Acme Supplies"
        )
        customer_headers = _register_and_login(
            client, mock_supabase_admin, mock_supabase_anon, role="CUSTOMER", full_name="Casey Customer"
        )

       
        category = client.post(
            "/categories", json={"name": "Kitchenware"}, headers=business_headers
        ).json()
        product = client.post(
            "/products",
            json={
                "sku": "KETTLE-1",
                "name": "Steel Kettle",
                "price": "24.99",
                "category_id": category["id"],
                "initial_quantity": 0,
            },
            headers=business_headers,
        ).json()
        assert product["available_quantity"] == 0

        supplier = client.post(
            "/suppliers", json={"name": "Kettle Wholesale", "contact_email": "sales@kw.example"},
            headers=business_headers,
        ).json()

        # Business orders stock from the supplier
        po = client.post(
            "/purchase-orders",
            json={
                "supplier_id": supplier["id"],
                "items": [{"product_id": product["id"], "quantity": 50, "unit_cost": "10.00"}],
            },
            headers=business_headers,
        ).json()
        assert po["total_amount"] == "500.00"

        received = client.patch(
            f"/purchase-orders/{po['id']}/status", json={"status": "RECEIVED"}, headers=business_headers
        )
        assert received.status_code == 200

        stock_after_receiving = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert stock_after_receiving["quantity"] == 50

        
        catalog = client.get("/products/list_products", headers=customer_headers).json()
        assert any(p["sku"] == "KETTLE-1" for p in catalog)

        order = client.post(
            "/orders", json={"items": [{"product_id": product["id"], "quantity": 3}]},
            headers=customer_headers,
        ).json()
        assert order["status"] == "CONFIRMED"
        assert order["total_amount"] == "74.97"

        stock_after_purchase = client.get(f"/inventory/{product['id']}", headers=business_headers).json()
        assert stock_after_purchase["quantity"] == 47

       
        fulfilled = client.patch(
            f"/orders/{order['id']}/status", json={"status": "COMPLETED"}, headers=business_headers
        )
        assert fulfilled.status_code == 200
        assert fulfilled.json()["status"] == "COMPLETED"

       
        my_orders = client.get("/orders/my-orders", headers=customer_headers).json()
        assert len(my_orders) == 1
        assert my_orders[0]["status"] == "COMPLETED"
