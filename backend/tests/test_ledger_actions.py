from decimal import Decimal
from fastapi.testclient import TestClient

def test_manual_entry_creation_and_stats(client: TestClient):
    # Register & Login Trader
    res = client.post("/api/v1/auth/register", json={"phone_number": "0711111222", "pin": "1234", "display_name": "Wanjiku"})
    assert res.status_code == 201
    tokens = res.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # 1. Create a Sale
    res_sale = client.post(
        "/api/v1/ledger",
        json={"entry_type": "sale", "item_description": "Nyanya 5kg", "amount_kes": "500.00", "is_settled": True},
        headers=headers,
    )
    assert res_sale.status_code == 201
    sale_id = res_sale.json()["id"]

    # 2. Create an Expense
    res_exp = client.post(
        "/api/v1/ledger",
        json={"entry_type": "expense", "item_description": "Nauli matatu", "amount_kes": "150.00", "is_settled": True},
        headers=headers,
    )
    assert res_exp.status_code == 201

    # 3. Create a Credit (Deni)
    res_credit = client.post(
        "/api/v1/ledger",
        json={
            "entry_type": "credit_given",
            "item_description": "Mchele 2kg",
            "amount_kes": "300.00",
            "counterparty_name": "Amina",
            "is_settled": False,
        },
        headers=headers,
    )
    assert res_credit.status_code == 201
    credit_id = res_credit.json()["id"]

    # Check stats
    stats_res = client.get("/api/v1/ledger/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert Decimal(str(stats["total_sales"])) == Decimal("500.00")
    assert Decimal(str(stats["total_expenses"])) == Decimal("150.00")
    assert Decimal(str(stats["outstanding_debt"])) == Decimal("300.00")
    assert Decimal(str(stats["net_cash_flow"])) == Decimal("350.00")
    assert stats["total_entries"] == 3

    # Update/Settle Credit entry
    patch_res = client.patch(
        f"/api/v1/ledger/{credit_id}",
        json={"is_settled": True},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_settled"] is True

    # Stats after settling debt
    stats_res2 = client.get("/api/v1/ledger/stats", headers=headers)
    assert Decimal(str(stats_res2.json()["outstanding_debt"])) == Decimal("0.00")

    # Delete entry
    del_res = client.delete(f"/api/v1/ledger/{sale_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify list count
    list_res = client.get("/api/v1/ledger", headers=headers)
    assert list_res.json()["total"] == 2


def test_cross_trader_isolation_on_new_endpoints(client: TestClient):
    # Trader A
    r1 = client.post("/api/v1/auth/register", json={"phone_number": "0722222333", "pin": "1234", "display_name": "Trader A"})
    t1 = r1.json()["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}

    # Trader B
    r2 = client.post("/api/v1/auth/register", json={"phone_number": "0733333444", "pin": "1234", "display_name": "Trader B"})
    t2 = r2.json()["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}

    # Trader A creates entry
    item_a = client.post(
        "/api/v1/ledger",
        json={"entry_type": "sale", "item_description": "Viazi bag 1", "amount_kes": "1200.00", "is_settled": True},
        headers=h1,
    ).json()

    # Trader B attempts to update Trader A's entry -> 404
    patch_attempt = client.patch(f"/api/v1/ledger/{item_a['id']}", json={"amount_kes": "1.00"}, headers=h2)
    assert patch_attempt.status_code == 404

    # Trader B attempts to delete Trader A's entry -> 404
    del_attempt = client.delete(f"/api/v1/ledger/{item_a['id']}", headers=h2)
    assert del_attempt.status_code == 404

    # Verify Trader A's entry is unaffected
    get_a = client.get(f"/api/v1/ledger/{item_a['id']}", headers=h1)
    assert get_a.status_code == 200
    assert Decimal(str(get_a.json()["amount_kes"])) == Decimal("1200.00")
