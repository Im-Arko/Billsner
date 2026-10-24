from app.ai.ocr_text import fix_rupee_ocr_errors


def test_fix_rupee_ocr_errors_corrects_common_misreads():
    text = "Subtotal 7366.00\nTax 765.88\nTotal 431.88"
    fixed = fix_rupee_ocr_errors(text)
    assert fixed == "Subtotal 366.00\nTax 65.88\nTotal 431.88"
    assert fix_rupee_ocr_errors(fixed) == fixed


def test_fix_rupee_ocr_errors_preserves_ambiguous_amounts():
    text = "Item total 766.00"
    assert fix_rupee_ocr_errors(text) == text


def test_fix_rupee_ocr_errors_preserves_balanced_real_amounts():
    text = "Subtotal 700.00\nTax 70.00\nTotal 770.00"
    assert fix_rupee_ocr_errors(text) == text


def test_fix_rupee_ocr_errors_is_independent_of_label_order():
    text = "Total 431.88\nSubtotal 7366.00\nTax 765.88"
    assert fix_rupee_ocr_errors(text) == "Total 431.88\nSubtotal 366.00\nTax 65.88"


def test_fix_rupee_ocr_errors_preserves_multiple_possible_corrections():
    text = "Subtotal 7366.00\nTax 765.88\nTotal 7431.88"
    assert fix_rupee_ocr_errors(text) == text


def test_fix_rupee_ocr_errors_preserves_digits_after_explicit_currency():
    text = "Subtotal ₹7366.00\nTax ₹65.88\nTotal ₹431.88"
    assert fix_rupee_ocr_errors(text) == text


def test_fix_rupee_ocr_errors_leaves_large_amounts_untouched():
    text = "Grand total 73596.00 and 712345.00"
    assert fix_rupee_ocr_errors(text) == text
