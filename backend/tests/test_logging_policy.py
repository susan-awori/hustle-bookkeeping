from app.logging_policy import redact_event_dict


def test_allowlist_keeps_safe_fields():
    cleaned = redact_event_dict(
        None,
        "info",
        {
            "event": "voice_parsed",
            "entry_type": "sale",
            "trader_id_hash": "abc",
            "transcript": "niliuza nyanya 200",
            "amount_kes": "200",
            "phone_number": "+254712345678",
            "unknown_field": "drop me",
        },
    )
    assert cleaned["event"] == "voice_parsed"
    assert cleaned["entry_type"] == "sale"
    assert cleaned["transcript"] == "[REDACTED]"
    assert cleaned["amount_kes"] == "[REDACTED]"
    assert cleaned["phone_number"] == "[REDACTED]"
    assert "unknown_field" not in cleaned
