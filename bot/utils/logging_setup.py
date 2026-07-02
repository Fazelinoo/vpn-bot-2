"""تنظیم logging."""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler

from bot.config import settings


def setup_logging() -> None:
    """پیکربندی logger با فایل چرخشی و console."""
    settings.log_dir.mkdir(parents=True, exist_ok=True)

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(logging.Formatter(log_format, date_format))
    root.addHandler(console)

    # File handler
    file_handler = RotatingFileHandler(
        settings.log_dir / "bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    root.addHandler(file_handler)

    # کاهش لاگ کتابخانه‌های پرحجم
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
