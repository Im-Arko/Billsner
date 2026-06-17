from app.ai.ocr_text import fix_rupee_ocr_errors


def test_fix_rupee_ocr_errors_corrects_common_misreads():
    text = "Subtotal 7366.00\nTax 7678.00\nTotal 7699.00"
    fixed = fix_rupee_ocr_errors(text)
    assert "366.00" in fixed
    assert "678.00" in fixed
    assert "699.00" in fixed
    assert "7366.00" not in fixed
    assert "7678.00" not in fixed
    assert "7699.00" not in fixed


def test_fix_rupee_ocr_errors_handles_two_digit_amounts():
    text = "Item total 766.00"
    assert fix_rupee_ocr_errors(text) == "Item total 66.00"


def test_fix_rupee_ocr_errors_leaves_large_amounts_untouched():
    text = "Grand total 73596.00 and 712345.00"
    assert fix_rupee_ocr_errors(text) == text
