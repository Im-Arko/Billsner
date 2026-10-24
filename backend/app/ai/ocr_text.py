"""Conservative correction of currency symbols misread as digits."""

from decimal import Decimal
from itertools import product
import re


def fix_rupee_ocr_errors(text: str) -> str:
    """Correct a spurious 7 only when subtotal + tax = total proves the change.

    A standalone 766.00 may be real. Without receipt arithmetic there is no
    reliable way to distinguish it from ₹66.00, so leave it unchanged.
    Balanced receipts and ambiguous corrections are also preserved.
    """
    matches = {}
    for match in re.finditer(
        r"^\s*(?P<label>sub\s*total|tax(?:\s+amount)?|(?:grand\s+)?total(?:\s+amount)?)"
        r"\s*[:=]?\s*(?P<currency>₹|Rs\.?|INR)?\s*(?P<amount>\d+\.\d{2})\s*$",
        text, re.IGNORECASE | re.MULTILINE,
    ):
        label = re.sub(r"\s+", "", match["label"].lower())
        key = "subtotal" if label == "subtotal" else "tax" if label.startswith("tax") else "total"
        if key in matches:
            return text
        matches[key] = match
    if set(matches) != {"subtotal", "tax", "total"}:
        return text

    ordered = [matches[key] for key in ("subtotal", "tax", "total")]
    original = tuple(Decimal(match["amount"]) for match in ordered)
    if original[0] + original[1] == original[2]:
        return text
    candidates = []
    for match, value in zip(ordered, original):
        amount = match["amount"]
        options = [value]
        if not match["currency"] and amount.startswith("7") and len(amount.split(".")[0]) > 1:
            options.append(Decimal(amount[1:]))
        candidates.append(options)
    valid = [values for values in product(*candidates) if values[0] + values[1] == values[2]]
    if len(valid) != 1:
        return text

    corrected = text
    replacements = sorted(zip(ordered, original, valid[0]), key=lambda item: item[0].start(), reverse=True)
    for match, before, after in replacements:
        if before != after:
            start, end = match.span("amount")
            corrected = corrected[:start] + match["amount"][1:] + corrected[end:]
    return corrected
