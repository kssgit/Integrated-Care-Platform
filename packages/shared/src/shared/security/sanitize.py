from __future__ import annotations

import html
import re


def validate_search_input(value: str, max_length: int = 100) -> bool:
    if len(value) > max_length:
        return False
    if re.search(r"[;\'\"\\]", value):
        return False
    return True


def sanitize_html_text(value: str) -> str:
    return html.escape(value, quote=True)

