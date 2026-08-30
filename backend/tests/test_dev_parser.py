from app.services.dev_parser import dev_parse_transcript


def test_dev_parse_sale():
    entries, confirmation, needs = dev_parse_transcript("I sold tomatoes for 200 shillings")
    assert not needs
    assert len(entries) == 1
    assert entries[0].entry_type.value == "sale"
    assert entries[0].amount_kes == 200
    assert "tomatoes" in entries[0].item_description.lower()
    assert confirmation


def test_dev_parse_requires_amount():
    entries, _, needs = dev_parse_transcript("I sold tomatoes")
    assert needs
    assert not entries
