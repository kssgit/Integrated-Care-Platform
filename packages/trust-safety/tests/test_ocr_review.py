import pytest

from trust_safety.ocr_review import verify_receipt_text


def test_verify_receipt_text_success() -> None:
    text = "Store: Seoul Care Pharmacy Total 12,500 KRW"
    assert verify_receipt_text(text, provider_keywords=["pharmacy", "care"], min_amount=5000)


def test_verify_receipt_text_fails_without_keyword() -> None:
    text = "Random Market Total 12,500 KRW"
    assert not verify_receipt_text(text, provider_keywords=["pharmacy"], min_amount=5000)


def test_verify_receipt_text_empty_keywords_raises() -> None:
    with pytest.raises(ValueError):
        verify_receipt_text("anything", provider_keywords=[])

