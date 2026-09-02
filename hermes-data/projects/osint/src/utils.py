import unicodedata


def normalize_polish(text: str) -> str:
    """Convert Polish letters to ASCII equivalents."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalize_for_api(text: str) -> str:
    """Normalize text for API queries that don't handle Unicode well."""
    return normalize_polish(text).replace(" ", "+")


def strip_accents(text: str) -> str:
    """Strip all unicode accents/diacritics."""
    return normalize_polish(text)
