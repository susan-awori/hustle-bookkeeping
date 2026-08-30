from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

import anthropic

from app.config import get_settings
from app.models import EntryType, PaymentMethod
from app.schemas import ParsedEntry

SYSTEM_PROMPT = """You are Hustle, a bookkeeping parser for informal Kenyan traders.
The user spoke mixed Kiswahili, Sheng, and English. Convert the transcript into ledger entries.

Rules:
- Currency is always Kenyan Shillings. "bob", "kee", "bob", "mia", "elfu" are KES.
- sale: money in from selling goods/services (niliuza, nimeuza, customer alilipa kwa bidhaa).
- expense: money out for stock or costs (nimenunua, nilinunua, nauli, rent, fuel).
- credit_given: goods sold on credit / deni — customer takes now, pays later (amechukua deni, nilipea kwa deni).
- credit_repaid: customer paying an old deni (amelipa deni, amerejesha).
- payment_method: cash for cash-in-hand sales, mpesa when they say M-Pesa/mobile money, credit only for credit_given.
- amounts must be numbers only, no commas. Use a string decimal like "150.00".
- If credit_given, is_settled=false and payment_method=credit. Sales paid immediately use entry_type=sale with payment_method cash or mpesa.
- If credit_repaid, include counterparty_name and payment_method cash or mpesa for how they paid back.
- counterparty_name required for credit_given / credit_repaid (customer name).
- Do not invent amounts. If the amount is missing, return entries=[] and needs_clarification=true.
- Never include phone numbers or PINs in any field.
- Reply with JSON only, matching the schema.
"""

USER_TEMPLATE = """Transcript:
{transcript}

Return JSON:
{{
  "entries": [
    {{
      "entry_type": "sale|expense|credit_given|credit_repaid",
      "item_description": "string",
      "amount_kes": "0.00",
      "counterparty_name": null,
      "payment_method": "cash|mpesa|credit",
      "is_settled": true
    }}
  ],
  "needs_clarification": false,
  "confirmation_text": "Short spoken confirmation in simple Kiswahili, e.g. Umeuza nyanya kwa shilingi mia mbili. Ni sawa?"
}}
"""


class ParseError(RuntimeError):
    pass


def translate_to_english(text: str) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key.strip():
        raise ParseError("Anthropic API key is not configured")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=800,
        system=(
            "You translate Kenyan Kiswahili, Sheng, and mixed Kiswahili-English into clear, "
            "natural English. Preserve names, numbers, currency, and meaning. Return only the "
            "translation, with no explanation or quotation marks."
        ),
        messages=[{"role": "user", "content": text}],
    )
    text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    if not text_blocks or not text_blocks[0].strip():
        raise ParseError("Empty translation response")
    return text_blocks[0].strip()


def parse_transcript(transcript: str) -> tuple[list[ParsedEntry], str, bool]:
    settings = get_settings()
    use_dev_parser = settings.environment in ("development", "test") and (
        not settings.anthropic_api_key.strip() or settings.anthropic_api_key.startswith("test-")
    )
    if use_dev_parser:
        from app.services.dev_parser import dev_parse_transcript

        return dev_parse_transcript(transcript)
    if not settings.anthropic_api_key.strip():
        raise ParseError("Anthropic API key is not configured")
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": USER_TEMPLATE.format(transcript=transcript)}],
    )
    text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    if not text_blocks:
        raise ParseError("Empty model response")
    raw = text_blocks[0].strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ParseError("Model did not return JSON") from exc
    needs = bool(payload.get("needs_clarification"))
    confirmation = str(payload.get("confirmation_text") or "Sijaelewa vizuri. Rudia kiasi na bidhaa.").strip()
    entries: list[ParsedEntry] = []
    for item in payload.get("entries") or []:
        try:
            amount = Decimal(str(item["amount_kes"]))
            if amount <= 0:
                continue
            entries.append(
                ParsedEntry(
                    entry_type=EntryType(item["entry_type"]),
                    item_description=str(item["item_description"])[:255],
                    amount_kes=amount.quantize(Decimal("0.01")),
                    counterparty_name=item.get("counterparty_name"),
                    payment_method=PaymentMethod(item.get("payment_method", PaymentMethod.cash.value)),
                    is_settled=bool(item.get("is_settled", True)),
                )
            )
        except (KeyError, InvalidOperation, ValueError):
            continue
    if not entries:
        needs = True
        if not payload.get("confirmation_text"):
            confirmation = "Sijapata kiasi. Tafadhali sema bidhaa na pesa, kwa mfano niliuza sukuma kwa shilingi hamsini."
    return entries, confirmation, needs
