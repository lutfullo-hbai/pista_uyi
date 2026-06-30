"""Validation utilities for input data."""

import re


def validate_phone(phone: str) -> bool:
    """Validate phone number format (basic Uzbek format)."""
    phone = phone.strip()
    # Accept formats like +998901234567, 998901234567, 901234567
    if phone.startswith("+"):
        phone = phone[1:]
    phone = re.sub(r"\D", "", phone)
    return len(phone) >= 9 and len(phone) <= 12


def validate_address(address: str) -> bool:
    """Validate address is not empty and reasonable length."""
    address = address.strip()
    return 3 <= len(address) <= 500


def validate_quantity(quantity: int) -> bool:
    """Validate product quantity."""
    return isinstance(quantity, int) and quantity > 0 and quantity <= 999


def validate_price(price: float) -> bool:
    """Validate product price."""
    return isinstance(price, (int, float)) and price > 0 and price < 1_000_000_000


def clean_phone(phone: str) -> str:
    """Clean phone number, removing extra characters."""
    phone = phone.strip()
    if phone.startswith("+"):
        phone = phone[1:]
    return phone


def parse_price_input(text: str) -> float | None:
    """Parse price from user input (handles currency words like 'so'm', 'sum')."""
    try:
        text = text.strip().lower()
        # Remove currency words
        for word in ["sum", "so'm", "soʻm", "som", "sóm", "сум"]:
            text = text.replace(word, "")
        text = text.strip().replace(" ", "").replace(",", "")
        price = float(text)
        if validate_price(price):
            return price
        return None
    except (ValueError, AttributeError):
        return None
