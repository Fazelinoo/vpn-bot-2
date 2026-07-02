"""Handler خرید پلن."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.repository import (
    SETTING_PRICE_PER_GB,
    SETTING_SALES_ENABLED,
    get_bool_setting,
    get_int_setting,
    get_plan_options,
)
from bot.keyboards.user_kb import back_to_menu_kb, payment_kb, plan_options_kb
from bot.utils.helpers import format_price

logger = logging.getLogger(__name__)
router = Router(name="purchase")


@router.callback_query(F.data == "buy_plan")
async def cb_buy_plan(callback: CallbackQuery, session: AsyncSession) -> None:
    """نمایش پلن‌ها."""
    if not await get_bool_setting(session, SETTING_SALES_ENABLED):
        await callback.answer("فروش در حال حاضر غیرفعال است.", show_alert=True)
        return

    price_per_gb = await get_int_setting(session, SETTING_PRICE_PER_GB)
    plans = await get_plan_options(session)

    if not plans:
        await callback.answer("پلنی تعریف نشده.", show_alert=True)
        return

    text = (
        "🛒 <b>خرید پلن VPN</b>\n\n"
        f"💰 قیمت هر گیگ: <b>{format_price(price_per_gb)}</b>\n\n"
        "پلن مورد نظر را انتخاب کنید:"
    )
    await callback.message.edit_text(
        text,
        reply_markup=plan_options_kb(plans, price_per_gb),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_plan:"))
async def cb_select_plan(callback: CallbackQuery, session: AsyncSession) -> None:
    """انتخاب پلن و نمایش اطلاعات پرداخت."""
    if not await get_bool_setting(session, SETTING_SALES_ENABLED):
        await callback.answer("فروش غیرفعال است.", show_alert=True)
        return

    gb = int(callback.data.split(":")[1])
    price_per_gb = await get_int_setting(session, SETTING_PRICE_PER_GB)
    total = gb * price_per_gb

    text = (
        f"📦 <b>پلن {gb} گیگ</b>\n\n"
        f"💰 مبلغ قابل پرداخت: <b>{format_price(total)}</b>\n"
        f"⏰ مدت اعتبار: <b>{settings.default_plan_days} روز</b>\n\n"
        "💳 <b>پرداخت کارت به کارت:</b>\n"
        f"<code>{settings.card_number}</code>\n"
        f"👤 {settings.card_holder}\n\n"
        "پس از واریز، روی «ارسال فیش» بزنید و عکس رسید را ارسال کنید."
    )
    await callback.message.edit_text(
        text,
        reply_markup=payment_kb(gb),
        parse_mode="HTML",
    )
    await callback.answer()
