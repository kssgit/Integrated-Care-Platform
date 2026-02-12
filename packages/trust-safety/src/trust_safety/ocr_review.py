import re


def normalize_ocr_text(text: str) -> str:
    return " ".join(text.lower().split())


def _extract_amounts(text: str) -> list[int]:
    numbers = re.findall(r"(?:\d{1,3}(?:,\d{3})+|\d+)", text)
    return [int(value.replace(",", "")) for value in numbers]


def verify_receipt_text(
    ocr_text: str,
    provider_keywords: list[str],
    min_amount: int = 1000,
) -> bool:
    normalized = normalize_ocr_text(ocr_text)
    if not provider_keywords:
        raise ValueError("provider_keywords must not be empty")
    found_keyword = any(keyword.lower() in normalized for keyword in provider_keywords)
    if not found_keyword:
        return False
    amounts = _extract_amounts(normalized)
    if not amounts:
        return False
    return max(amounts) >= min_amount

