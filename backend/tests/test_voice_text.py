def test_parse_text_dev(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"phone_number": "0712345679", "pin": "1234", "display_name": "Dev Parser"},
    )
    token = register.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/api/v1/voice/parse-text",
        headers=headers,
        json={"text": "I sold tomatoes for 200 shillings"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["transcript"] == "I sold tomatoes for 200 shillings"
    assert len(payload["entries"]) == 1
    assert payload["entries"][0]["entry_type"] == "sale"
