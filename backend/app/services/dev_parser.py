"""Lightweight transcript parser for local development without Anthropic."""

from __future__ import annotations

import re
from decimal import Decimal

from app.models import EntryType
from app.schemas import ParsedEntry

SALE_WORDS = ("sold", "sell", "niliuza", "nimeuza", "mauzo", "uza", "uza")
EXPENSE_WORDS = ("bought", "buy", "nimenunua", "nilinunua", "matumizi", "nunua", "rent", "fuel", "nauli")
CREDIT_GIVEN = ("deni", "credit", "amechukua", "nilipea")
CREDIT_REPAID = ("amelipa", "repaid", "malipo ya deni", "rejesha", "amerejesha")


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
    ):
        item = re.sub(rf"\b{re.escape(word)}\b", "", item, flags=re.I)
    item = re.sub(r"\s+", " ", item).strip(" ,.-") or "Bidhaa"

    entry = ParsedEntry(
        entry_type=entry_type,
        item_description=item[:255],
        amount_kes=amount,
        counterparty_name=None,
        is_settled=entry_type is not EntryType.credit_given,
    )
    confirmation = f"Umeandika {entry.item_description} kwa shilingi {amount}. Ni sawa?"
    return [entry], confirmation, False
