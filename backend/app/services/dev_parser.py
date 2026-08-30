"""Lightweight transcript parser for local development without Anthropic."""

from __future__ import annotations

import re
from decimal import Decimal

from app.models import EntryType, PaymentMethod
from app.schemas import ParsedEntry

SALE_WORDS = ("sold", "sell", "niliuza", "nimeuza", "mauzo", "uza")
EXPENSE_WORDS = ("bought", "buy", "nimenunua", "nilinunua", "matumizi", "nunua", "rent", "fuel", "nauli")
CREDIT_GIVEN = ("deni", "credit", "amechukua", "nilipea", "on credit", "bila kulipa")
CREDIT_REPAID = ("amelipa", "repaid", "malipo ya deni", "rejesha", "amerejesha", "paid back")
MPESA_WORDS = ("mpesa", "m-pesa", "mobile money", "phone money")
CASH_WORDS = ("cash", "pesa taslimu", "mkono", "cash sale")


def _extract_counterparty(text: str) -> str | None:
    patterns = (
        r"(?:to|kwa|for|from|wa)\s+([A-Za-z][A-Za-z'\- ]{1,40})",
        r"(?:nilipea|nlimpa|customer)\s+([A-Za-z][A-Za-z'\- ]{1,40})",
        r"(?:deni\s+kwa|credit\s+to)\s+([A-Za-z][A-Za-z'\- ]{1,40})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        name = match.group(1).strip(" .,").split()[0]
        lowered = name.lower()
        if lowered in {"mpesa", "cash", "deni", "credit", "shillings", "shilingi", "bob", "nyanya", "tomatoes"}:
            continue
        return name[:120]
    return None


def _detect_payment_method(lower: str, entry_type: EntryType) -> PaymentMethod:
    if entry_type is EntryType.credit_given:
        return PaymentMethod.credit
    if any(word in lower for word in MPESA_WORDS):
        return PaymentMethod.mpesa
    if any(word in lower for word in CASH_WORDS):
        return PaymentMethod.cash
    if entry_type in (EntryType.sale, EntryType.credit_repaid):
        return PaymentMethod.cash
    return PaymentMethod.cash


def dev_parse_transcript(transcript: str) -> tuple[list[ParsedEntry], str, bool]:
    text = transcript.strip()
    if not text:
        return [], "Sijaelewa. Sema tena.", True

    amounts = re.findall(r"\d+(?:\.\d{1,2})?", text)
    if not amounts:
        return [], "Sijapata kiasi. Tafadhali sema tena na kiasi.", True

    amount = Decimal(amounts[-1]).quantize(Decimal("0.01"))
    lower = text.lower()

    if any(word in lower for word in CREDIT_REPAID):
        entry_type = EntryType.credit_repaid
    elif any(word in lower for word in CREDIT_GIVEN):
        entry_type = EntryType.credit_given
    elif any(word in lower for word in EXPENSE_WORDS):
        entry_type = EntryType.expense
    elif any(word in lower for word in SALE_WORDS):
        entry_type = EntryType.sale
    else:
        entry_type = EntryType.sale

    payment_method = _detect_payment_method(lower, entry_type)
    counterparty = _extract_counterparty(text)
    if entry_type in (EntryType.credit_given, EntryType.credit_repaid) and not counterparty:
        return [], "Taja jina la mteja kwa deni.", True

    item = re.sub(r"\d+(?:\.\d{1,2})?", "", text)
    for word in (
        "shillings",
        "shilingi",
        "bob",
        "kes",
        "for",
        "kwa",
        "the",
        "a",
        "an",
        "i",
        "my",
        "nili",
        "nime",
        "mpesa",
        "m-pesa",
        "cash",
        "deni",
        "credit",
        "via",
        "through",
    ):
        item = re.sub(rf"\b{re.escape(word)}\b", "", item, flags=re.I)
    if counterparty:
        item = re.sub(rf"\b{re.escape(counterparty)}\b", "", item, flags=re.I)
    item = re.sub(r"\s+", " ", item).strip(" ,.-") or "Bidhaa"

    entry = ParsedEntry(
        entry_type=entry_type,
        item_description=item[:255],
        amount_kes=amount,
        counterparty_name=counterparty,
        payment_method=payment_method,
        is_settled=entry_type is not EntryType.credit_given,
    )

    if entry_type is EntryType.credit_given:
        who = counterparty or "mteja"
        confirmation = f"Umemuachia {who} {entry.item_description} kwa deni ya shilingi {amount}. Ni sawa?"
    elif payment_method is PaymentMethod.mpesa:
        confirmation = f"Umeuza {entry.item_description} kwa M-Pesa shilingi {amount}. Ni sawa?"
    elif entry_type is EntryType.sale:
        confirmation = f"Umeuza {entry.item_description} kwa pesa taslimu shilingi {amount}. Ni sawa?"
    else:
        confirmation = f"Umeandika {entry.item_description} kwa shilingi {amount}. Ni sawa?"
    return [entry], confirmation, False
