from decimal import Decimal
from uuid import UUID

from app.models import EntryType
from app.repositories import ledger as ledger_repo


def _register(client, phone: str, name: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"phone_number": phone, "pin": "2468", "display_name": name},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_ledger_is_scoped_to_authenticated_trader(client, db):
    token_a = _register(client, "0711111111", "Amina")
    token_b = _register(client, "0722222222", "Juma")

    me_a = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a}"}).json()
    me_b = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_b}"}).json()

    ledger_repo.insert_entry(
        db,
        trader_id=UUID(me_a["id"]),
        entry_type=EntryType.sale,
        item_description="sukuma",
        amount_kes=Decimal("50.00"),
        counterparty_name=None,
        is_settled=True,
        raw_transcript="niliuza sukuma 50",
    )
    ledger_repo.insert_entry(
        db,
        trader_id=UUID(me_b["id"]),
        entry_type=EntryType.expense,
        item_description="unga",
        amount_kes=Decimal("200.00"),
        counterparty_name=None,
        is_settled=True,
        raw_transcript="nimenunua unga 200",
    )

    listed_a = client.get("/api/v1/ledger", headers={"Authorization": f"Bearer {token_a}"}).json()
    listed_b = client.get("/api/v1/ledger", headers={"Authorization": f"Bearer {token_b}"}).json()
    assert listed_a["total"] == 1
    assert listed_a["items"][0]["item_description"] == "sukuma"
    assert listed_b["total"] == 1
    assert listed_b["items"][0]["item_description"] == "unga"

    foreign_id = listed_b["items"][0]["id"]
    sneak = client.get(f"/api/v1/ledger/{foreign_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert sneak.status_code == 404
