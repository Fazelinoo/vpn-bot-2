"""Middleware ضد اسپم."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class ThrottlingMiddleware(BaseMiddleware):
    """محدودیت نرخ درخواست برای هر کاربر."""

    def __init__(self, rate_limit: float = 0.5) -> None:
        self.rate_limit = rate_limit
        self._last_request: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            now = time.monotonic()
            last = self._last_request.get(user_id, 0)
            if now - last < self.rate_limit:
                if isinstance(event, Message):
                    await event.answer("⏳ لطفاً کمی صبر کنید...")
                return None
            self._last_request[user_id] = now

            # پاکسازی حافظه
            if len(self._last_request) > 10000:
                cutoff = now - 60
                self._last_request = {
                    k: v for k, v in self._last_request.items() if v > cutoff
                }

        return await handler(event, data)
