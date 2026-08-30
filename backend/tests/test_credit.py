from decimal import Decimal
from uuid import UUID

from app.models import EntryType, PaymentMethod
from app.repositories import ledger as ledger_repo


def _register(client, phone: str, name: str) -> str:
    response = client.post(
        "/api/v1/auth/register",
        json={"phone_number": phone, "pin": "2468", "display_name": name},
    )
    assert response.status_code == 201
    return response.json()["access_token"]


def test_outstanding_credit_and_repay(client, db):
    token = _register(client, "0733333333", "Credit Trader")
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    ledger_repo.insert_entry(
        db,
        trader_id=UUID(me["id"]),
        entry_type=EntryType.credit_given,
        item_description="nyanya",
        amount_kes=Decimal("300.00"),
        counterparty_name="Amina",
        payment_method=PaymentMethod.credit,
        is_settled=False,
        raw_transcript="deni kwa Amina",
    )

    outstanding = client.get(
        "/api/v1/ledger/credit/outstanding",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert outstanding["total"] == 1
    assert outstanding["amount_due_kes"] == "300.00"
    entry_id = outstanding["items"][0]["id"]

    repaid = client.post(
        f"/api/v1/ledger/{entry_id}/repay",
        headers={"Authorization": f"Bearer {token}"},
        json={"payment_method": "mpesa"},
    )
    assert repaid.status_code == 200
    payload = repaid.json()
    assert len(payload) == 2
    assert payload[0]["is_settled"] is True
    assert payload[1]["entry_type"] == "credit_repaid"
    assert payload[1]["payment_method"] == "mpesa"

    outstanding_after = client.get(
        "/api/v1/ledger/credit/outstanding",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert outstanding_after["total"] == 0
