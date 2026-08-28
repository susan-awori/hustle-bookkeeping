def test_register_and_login(client):
    payload = {"phone_number": "0712345678", "pin": "1234", "display_name": "Mama Amina"}
    created = client.post("/api/v1/auth/register", json=payload)
    assert created.status_code == 201
    tokens = created.json()
    assert tokens["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert me.status_code == 200
    assert me.json()["display_name"] == "Mama Amina"
    assert "phone" not in me.json()

    login = client.post("/api/v1/auth/login", json={"phone_number": "+254712345678", "pin": "1234"})
    assert login.status_code == 200

    bad = client.post("/api/v1/auth/login", json={"phone_number": "+254712345678", "pin": "0000"})
    assert bad.status_code == 401


def test_rejects_short_pin(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"phone_number": "0712345678", "pin": "12", "display_name": "X"},
    )
    assert response.status_code == 422
