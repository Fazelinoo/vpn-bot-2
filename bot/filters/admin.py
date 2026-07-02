"""فیلترهای سفارشی."""

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import settings
from bot.utils.helpers import is_admin


class AdminFilter(BaseFilter):
    """فقط ادمین‌ها."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user
        return user is not None and is_admin(user.id, settings.admin_ids)
