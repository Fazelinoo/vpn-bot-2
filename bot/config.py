"""تنظیمات ربات از متغیرهای محیطی."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _parse_admin_ids(raw: str) -> list[int]:
    """تبدیل رشته ADMIN_IDS به لیست عددی."""
    if not raw.strip():
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


@dataclass(frozen=True)
class Settings:
    """تنظیمات اصلی برنامه."""

    # Telegram
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    admin_ids: list[int] = field(
        default_factory=lambda: _parse_admin_ids(os.getenv("ADMIN_IDS", ""))
    )

    # 3x-ui Panel
    xui_host: str = field(
        default_factory=lambda: os.getenv(
            "XUI_HOST",
            "https://vp2.fazelino.lol:2053/DX9BkswG96YruEosP4",
        )
    )
    xui_token: str = field(
        default_factory=lambda: os.getenv("XUI_TOKEN", "")
    )
    xui_use_tls_verify: bool = field(
        default_factory=lambda: os.getenv("XUI_USE_TLS_VERIFY", "false").lower()
        == "true"
    )

    # Subscription
    subscription_base_url: str = field(
        default_factory=lambda: os.getenv(
            "SUBSCRIPTION_BASE_URL",
            "https://vp2.fazelino.lol:2053/DX9BkswG96YruEosP4",
        )
    )
    subscription_domain: str = field(
        default_factory=lambda: os.getenv("SUBSCRIPTION_DOMAIN", "fazelino.lol")
    )

    # Payment
    card_number: str = field(
        default_factory=lambda: os.getenv("CARD_NUMBER", "6037997501682950")
    )
    card_holder: str = field(
        default_factory=lambda: os.getenv("CARD_HOLDER", "فروشگاه VPN")
    )

    # Database
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'bot.db'}"
        )
    )

    # Defaults
    default_plan_days: int = field(
        default_factory=lambda: int(os.getenv("DEFAULT_PLAN_DAYS", "30"))
    )
    free_trial_gb: float = field(
        default_factory=lambda: float(os.getenv("FREE_TRIAL_GB", "1"))
    )
    free_trial_days: int = field(
        default_factory=lambda: int(os.getenv("FREE_TRIAL_DAYS", "1"))
    )
    free_trial_cooldown_hours: int = field(
        default_factory=lambda: int(os.getenv("FREE_TRIAL_COOLDOWN_HOURS", "24"))
    )

    # Anti-spam
    throttle_rate: float = field(
        default_factory=lambda: float(os.getenv("THROTTLE_RATE", "0.5"))
    )

    # Logging
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    log_dir: Path = field(default_factory=lambda: BASE_DIR / "logs")

    def validate(self) -> None:
        """اعتبارسنجی تنظیمات ضروری."""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN در فایل .env تنظیم نشده است.")
        if not self.admin_ids:
            raise ValueError("حداقل یک ADMIN_ID در فایل .env لازم است.")
        if not self.xui_host or not self.xui_token:
            raise ValueError("XUI_HOST و XUI_TOKEN باید تنظیم شوند.")


settings = Settings()
