"""Handler ادمین — مدیریت کاربران."""

from __future__ import annotations

import logging
import math

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin import AdminFilter
from bot.database.models import OrderStatus
from bot.database.repository import (
    count_users,
    get_user_orders,
    list_users,
    search_users,
)
from bot.keyboards.admin_kb import admin_back_kb, user_actions_kb, users_list_kb
from bot.states.states import AdminStates

logger = logging.getLogger(__name__)
router = Router(name="admin_users")
admin_filter = AdminFilter()

PAGE_SIZE = 15


@router.callback_query(F.data == "admin_users", admin_filter)
async def cb_admin_users(callback: CallbackQuery, session: AsyncSession) -> None:
    """لیست کاربران — صفحه ۰."""
    await _show_users_page(callback, session, 0)


@router.callback_query(F.data.startswith("admin_users_page:"), admin_filter)
async def cb_users_page(callback: CallbackQuery, session: AsyncSession) -> None:
    """صفحه‌بندی کاربران."""
    page = int(callback.data.split(":")[1])
    await _show_users_page(callback, session, page)


async def _show_users_page(
    callback: CallbackQuery, session: AsyncSession, page: int
) -> None:
    """نمایش صفحه کاربران."""
    total = await count_users(session)
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    page = max(0, min(page, total_pages - 1))

    users = await list_users(session, offset=page * PAGE_SIZE, limit=PAGE_SIZE)
    await callback.message.edit_text(
        f"👥 <b>کاربران</b> ({total} نفر)",
        reply_markup=users_list_kb(users, page, total_pages),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_search_user", admin_filter)
async def cb_search_user(callback: CallbackQuery, state) -> None:
    """جستجوی کاربر."""
    await state.set_state(AdminStates.search_user)
    await callback.message.edit_text(
        "🔍 یوزرنیم، نام یا آیدی عددی کاربر را ارسال کنید:",
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.search_user, admin_filter)
async def on_search_user(message: Message, session: AsyncSession, state) -> None:
    """نتیجه جستجو."""
    if not message.text:
        return
    query = message.text.strip()
    users = await search_users(session, query)
    await state.clear()

    if not users:
        await message.answer("کاربری یافت نشد.", reply_markup=admin_back_kb())
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton

    builder = InlineKeyboardBuilder()
    for u in users:
        name = u.username or u.full_name or str(u.id)
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {name} ({u.id})",
                callback_data=f"admin_user:{u.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 پنل", callback_data="admin_panel"))

    await message.answer(
        f"🔍 {len(users)} نتیجه:",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("admin_user:"), admin_filter)
async def cb_admin_user(callback: CallbackQuery, session: AsyncSession) -> None:
    """جزئیات کاربر."""
    user_id = int(callback.data.split(":")[1])
    orders = await get_user_orders(session, user_id)
    active_ids = [o.id for o in orders if o.status == OrderStatus.ACTIVE]

    text = (
        f"👤 <b>کاربر</b> <code>{user_id}</code>\n\n"
        f"📦 تعداد اکانت: {len(orders)}\n"
        f"🟢 فعال: {len(active_ids)}"
    )
    await callback.message.edit_text(
        text,
        reply_markup=user_actions_kb(user_id, active_ids),
        parse_mode="HTML",
    )
    await callback.answer()
