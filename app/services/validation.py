import re

MAX_TEXT = 2500
MAX_TITLE = 120
MAX_GENRES = 180


def clean_text(value: str, limit: int = MAX_TEXT) -> str:
    value = re.sub(r"\s+", " ", value or "").strip()
    return value[:limit]


def parse_season(value: str) -> int | None:
    match = re.fullmatch(r"(?:season\s*)?(\d{1,3})", value.strip(), re.I)
    if not match:
        return None
    number = int(match.group(1))
    return number if number >= 1 else None


def valid_title(value: str) -> bool:
    return 1 <= len(clean_text(value, MAX_TITLE)) <= MAX_TITLE
