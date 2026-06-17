"""OCR text cleanup helpers."""

from __future__ import annotations

import re


def fix_rupee_ocr_errors(text: str) -> str:
    """
    Fix amounts where OCR misread ₹ as a leading '7'.

    Examples:
    76.00 -> 6.00
    766.00 -> 66.00
    7366.00 -> 366.00
    7678.00 -> 678.00

    Leaves legitimate amounts (e.g. 73596.00, 712345.00) unchanged.
    """

    def replace_match(match: re.Match[str]) -> str:
        amount = match.group(0)
        corrected = amount[1:]

        try:
            original_val = float(amount)
            corrected_val = float(corrected)
            integer_digits = len(corrected.split(".", maxsplit=1)[0])
            expected_diff = 7 * (10**integer_digits)
            if (
                abs(original_val - corrected_val - expected_diff) < 0.01
                and corrected_val < 2000
            ):
                return corrected
        except ValueError:
            pass

        return amount

    return re.sub(r"\b7\d{1,3}\.\d{2}\b", replace_match, text)
