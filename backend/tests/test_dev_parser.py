from app.models import EntryType, PaymentMethod
from app.services.dev_parser import dev_parse_transcript


def test_dev_parse_cash_sale():
    entries, _, needs = dev_parse_transcript("I sold tomatoes for 200 cash")
    assert not needs
    assert entries[0].entry_type == EntryType.sale
    assert entries[0].payment_method == PaymentMethod.cash


def test_dev_parse_mpesa_sale():
    entries, _, needs = dev_parse_transcript("Niliuza sukuma 150 via mpesa")
    assert not needs
    assert entries[0].entry_type == EntryType.sale
    assert entries[0].payment_method == PaymentMethod.mpesa


def test_dev_parse_credit_sale():
    entries, _, needs = dev_parse_transcript("Nilipea Amina nyanya 300 kwa deni")
    assert not needs
    assert entries[0].entry_type == EntryType.credit_given
    assert entries[0].payment_method == PaymentMethod.credit
    assert entries[0].counterparty_name == "Amina"
    assert entries[0].is_settled is False


def test_dev_parse_credit_requires_name():
    entries, _, needs = dev_parse_transcript("Sold on credit for 200")
    assert needs
    assert not entries
