from datetime import datetime


def utc_timestamp(value: datetime) -> str:
    return value.isoformat()


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def emails_match(email_a: str | None, email_b: str | None) -> bool:
    return normalize_email(email_a) == normalize_email(email_b)
