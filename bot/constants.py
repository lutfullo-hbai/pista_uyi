"""
Constants and configuration utilities.
"""

# Status constants
PRODUCT_STATUS = {
    "available": True,
    "unavailable": False,
}

ORDER_STATUS = {
    "pending": "pending",
    "processing": "processing",
    "delivered": "delivered",
    "cancelled": "cancelled",
}

VALID_ORDER_STATUSES = list(ORDER_STATUS.values())

# Limits
MAX_PRODUCT_NAME_LENGTH = 255
MAX_PRODUCT_DESCRIPTION_LENGTH = 2000
MAX_ADDRESS_LENGTH = 500
MAX_QUANTITY_PER_ITEM = 999
MAX_ITEMS_PER_ORDER = 100

# Prices
MIN_PRICE = 100
MAX_PRICE = 1_000_000_000

# Phone validation
MIN_PHONE_LENGTH = 9
MAX_PHONE_LENGTH = 12

# Pagination
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Cache durations (seconds)
CACHE_CATEGORIES_TTL = 3600  # 1 hour
CACHE_PRODUCTS_TTL = 1800    # 30 minutes
CACHE_STATS_TTL = 300        # 5 minutes
