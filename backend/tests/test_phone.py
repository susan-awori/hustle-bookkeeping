import pytest

from app.security import normalize_ke_phone


def test_local_and_e164():
    assert normalize_ke_phone("0712345678") == "+254712345678"
    assert normalize_ke_phone("+254712345678") == "+254712345678"
    assert normalize_ke_phone("712345678") == "+254712345678"


def test_rejects_landline_shaped():
    with pytest.raises(ValueError):
        normalize_ke_phone("020123456")
