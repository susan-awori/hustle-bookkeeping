from fastapi.testclient import TestClient

def test_full_e2e_frontend_to_backend_workflow(client: TestClient):
    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}

    # 2. Get merchant profile (zero-barrier auto-provisioning)
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 200
    me = res.json()
    assert me["display_name"] == "Mama Boi Groceries"

    # 3. Create a custom transaction (as frontend sends)
    payload = {
        "entry_type": "sale",
        "item_description": "3 blankets",
        "amount_kes": "1500.00",
        "counterparty_name": None,
        "is_settled": True
    }
    res = client.post("/api/v1/ledger", json=payload)
    assert res.status_code == 201
    created = res.json()
    assert created["item_description"] == "3 blankets"
    assert created["amount_kes"] == "1500.00"

    # 4. Fetch ledger feed (as Flutter & Web frontend fetch)
    res = client.get("/api/v1/ledger")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    items = data["items"]
    assert any(i["item_description"] == "3 blankets" for i in items)

    # 5. Fetch ledger stats
    res = client.get("/api/v1/ledger/stats")
    assert res.status_code == 200
    stats = res.json()
    assert float(stats["total_sales"]) >= 1500.0
