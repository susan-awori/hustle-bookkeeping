from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

import anthropic

from app.config import get_settings
from app.models import EntryType
from app.schemas import ParsedEntry

SYSTEM_PROMPT = """You are Hustle, a bookkeeping parser for informal Kenyan traders.
The user spoke mixed Kiswahili, Sheng, and English. Convert the transcript into ledger entries.

Rules:
- Currency is always Kenyan Shillings. "bob", "kee", "mia", "elfu" are KES.
- sale: money in from selling goods/services (niliuza, nimeuza, customer alilipa kwa bidhaa, sold, sale).
- expense: money out for stock or costs (nimenunua, nilinunua, nauli, rent, fuel, bought, paid).
- credit_given: goods/service given now, money later (deni, nilipea credit, amechukua deni, owes).
- credit_repaid: customer paying an old deni (amelipa deni, amerejesha, paid back).
- amounts must be numbers only, no commas. Use a string decimal like "150.00".
- If credit_given, is_settled=false. If credit_repaid or sale/expense, is_settled=true unless they said otherwise.
- counterparty_name only for credit_given / credit_repaid.
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
      "is_settled": true
    }}
  ],
  "needs_clarification": false,
  "confirmation_text": "Short spoken confirmation in simple Kiswahili or English, e.g. Record created."
}}
"""


class ParseError(RuntimeError):
    pass


def translate_to_english(text: str) -> str:
    settings = get_settings()
    if not settings.anthropic_api_key.strip():
        return text

    try:
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
        if text_blocks and text_blocks[0].strip():
            return text_blocks[0].strip()
    except Exception:
        pass
    return text


def dynamic_regex_parse(transcript: str) -> tuple[list[ParsedEntry], str, bool]:
    """Dynamic NLP regex extractor for ANY custom user sentence."""
    text = transcript.strip()
    text_lower = text.lower()

    # Extract numbers (e.g. 1500, 450.00, 200)
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", text)
    amount = Decimal("100.00")
    if numbers:
        try:
            amount = Decimal(numbers[-1])
        except Exception:
            amount = Decimal("100.00")

    # Determine entry type
    entry_type = EntryType.sale
    if any(k in text_lower for k in ["expense", "bought", "spent", "paid for", "nilitumia", "nilinunua", "nauli", "rent", "fuel", "kutoa"]):
        entry_type = EntryType.expense
    elif any(k in text_lower for k in ["owes", "credit", "debt", "deni", "ananidai"]):
        entry_type = EntryType.credit_given
    elif any(k in text_lower for k in ["paid back", "repaid", "amelipa deni"]):
        entry_type = EntryType.credit_repaid

    # Extract item description dynamically from sentence
    clean_item = text
    # Remove common fill words and amounts from description
    clean_item = re.sub(r"\b(?:sold|bought|spent|paid|for|niliuza|nilinunua|kes|shilling|shillings|bob|m-pesa|mpesa)\b", "", clean_item, flags=re.IGNORECASE)
    clean_item = re.sub(r"\b\d+(?:\.\d+)?\b", "", clean_item).strip()
    if not clean_item or len(clean_item) < 2:
        clean_item = text

    # Extract counterparty name if credit entry
    counterparty = None
    if entry_type in (EntryType.credit_given, EntryType.credit_repaid):
        words = text.split()
        for w in words:
            if w[0].isupper() and w.lower() not in ["kes", "sold", "bought", "m-pesa"]:
                counterparty = w
                break

    is_settled = entry_type != EntryType.credit_given

    entry = ParsedEntry(
        entry_type=entry_type,
        item_description=clean_item[:255],
        amount_kes=amount,
        counterparty_name=counterparty,
        is_settled=is_settled,
    )
    confirmation = f"Recorded {entry_type.value}: {clean_item} for KES {amount}"
    return [entry], confirmation, False


def parse_transcript(transcript: str) -> tuple[list[ParsedEntry], str, bool]:
    settings = get_settings()
    if not settings.anthropic_api_key.strip():
        return dynamic_regex_parse(transcript)

    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=800,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_TEMPLATE.format(transcript=transcript)}],
        )
        text_blocks = [block.text for block in message.content if getattr(block, "type", None) == "text"]
        if text_blocks:
            raw = text_blocks[0].strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            payload = json.loads(raw)
            needs = bool(payload.get("needs_clarification"))
            confirmation = str(payload.get("confirmation_text") or "Recorded entry.").strip()
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
                            is_settled=bool(item.get("is_settled", True)),
                        )
                    )
                except (KeyError, InvalidOperation, ValueError):
                    continue
            if entries:
                return entries, confirmation, needs
    except Exception:
        pass

    return dynamic_regex_parse(transcript)
