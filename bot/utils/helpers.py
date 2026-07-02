"""توابع کمکی."""

from __future__ import annotations

from datetime import datetime, timezone


def format_bytes(size: float) -> str:
    """فرمت حجم به گیگ/مگ."""
    gb = 1024**3
    mb = 1024**2
    if size >= gb:
        return f"{size / gb:.2f} GB"
    if size >= mb:
        return f"{size / mb:.2f} MB"
    return f"{size:.0f} B"


def format_price(amount: int) -> str:
    """فرمت قیمت با جداکننده هزار."""
    return f"{amount:,} تومان"


def format_datetime(dt: datetime | None) -> str:
    """فرمت تاریخ شمسی‌نما (میلادی ساده)."""
    if not dt:
        return "نامحدود"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    local = dt.astimezone()
    return local.strftime("%Y-%m-%d %H:%M")


def is_admin(user_id: int, admin_ids: list[int]) -> bool:
    """بررسی ادمین بودن."""
    return user_id in admin_ids
