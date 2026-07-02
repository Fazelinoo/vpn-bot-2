"""Handler پنل ادمین — منوی اصلی و آمار."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repository import (
    SETTING_FREE_TRIAL_ENABLED,
    SETTING_PLAN_GB_OPTIONS,
    SETTING_PRICE_PER_GB,
    SETTING_SALES_ENABLED,
    get_bool_setting,
    get_int_setting,
    get_setting,
    get_stats,
    set_setting,
)
from bot.filters.admin import AdminFilter
from bot.keyboards.admin_kb import admin_back_kb, admin_panel_kb
from bot.states.states import AdminStates
from bot.utils.helpers import format_price

logger = logging.getLogger(__name__)
router = Router(name="admin_panel")
admin_filter = AdminFilter()


@router.message(Command("admin"), admin_filter)
async def cmd_admin(message: Message) -> None:
    """دستور /admin."""
    await message.answer(
        "⚙️ <b>پنل مدیریت</b>\n\nگزینه مورد نظر را انتخاب کنید:",
        reply_markup=admin_panel_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_panel", admin_filter)
async def cb_admin_panel(callback: CallbackQuery) -> None:
    """منوی ادمین."""
    await callback.message.edit_text(
        "⚙️ <b>پنل مدیریت</b>\n\nگزینه مورد نظر را انتخاب کنید:",
        reply_markup=admin_panel_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "admin_stats", admin_filter)
async def cb_admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    """نمایش آمار."""
    stats = await get_stats(session)
    price = await get_int_setting(session, SETTING_PRICE_PER_GB)

    text = (
        "📊 <b>آمار کلی</b>\n\n"
        f"👥 کل کاربران: <b>{stats['total_users']}</b>\n"
        f"🟢 کاربران فعال: <b>{stats['active_users']}</b>\n"
        f"📈 فروش امروز: <b>{stats['today_sales']}</b>\n"
        f"📅 فروش این ماه: <b>{stats['month_sales']}</b>\n"
        f"💰 درآمد کل: <b>{format_price(stats['total_revenue'])}</b>\n"
        f"🧾 فیش در انتظار: <b>{stats['pending_payments']}</b>\n\n"
        f"💵 قیمت هر گیگ: <b>{format_price(price)}</b>"
    )
    await callback.message.edit_text(
        text, reply_markup=admin_back_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_price", admin_filter)
async def cb_admin_price(callback: CallbackQuery, session: AsyncSession, state) -> None:
    """تنظیم قیمت."""
    current = await get_int_setting(session, SETTING_PRICE_PER_GB)
    await state.set_state(AdminStates.set_price)
    await callback.message.edit_text(
        f"💰 قیمت فعلی هر گیگ: <b>{format_price(current)}</b>\n\n"
        "قیمت جدید (تومان) را ارسال کنید:",
        reply_markup=admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.set_price, admin_filter)
async def on_set_price(message: Message, session: AsyncSession, state) -> None:
    """ذخیره قیمت."""
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ عدد معتبر وارد کنید.")
        return

    price = int(message.text.strip())
    await set_setting(session, SETTING_PRICE_PER_GB, str(price))
    await state.clear()
    await message.answer(
        f"✅ قیمت هر گیگ: {format_price(price)}",
        reply_markup=admin_panel_kb(),
    )
    logger.info("قیمت هر گیگ به %s تغییر کرد", price)


@router.callback_query(F.data == "admin_toggle_sales", admin_filter)
async def cb_toggle_sales(callback: CallbackQuery, session: AsyncSession) -> None:
    """فعال/غیرفعال فروش."""
    current = await get_bool_setting(session, SETTING_SALES_ENABLED)
    new_val = "false" if current else "true"
    await set_setting(session, SETTING_SALES_ENABLED, new_val)
    status = "فعال ✅" if not current else "غیرفعال ❌"
    await callback.answer(f"فروش {status}", show_alert=True)
    logger.info("فروش: %s", status)


@router.callback_query(F.data == "admin_toggle_trial", admin_filter)
async def cb_toggle_trial(callback: CallbackQuery, session: AsyncSession) -> None:
    """فعال/غیرفعال تست رایگان."""
    current = await get_bool_setting(session, SETTING_FREE_TRIAL_ENABLED)
    new_val = "false" if current else "true"
    await set_setting(session, SETTING_FREE_TRIAL_ENABLED, new_val)
    status = "فعال ✅" if not current else "غیرفعال ❌"
    await callback.answer(f"تست رایگان {status}", show_alert=True)


@router.callback_query(F.data == "admin_plans", admin_filter)
async def cb_admin_plans(callback: CallbackQuery, session: AsyncSession, state) -> None:
    """تنظیم پلن‌ها."""
    current = await get_setting(session, SETTING_PLAN_GB_OPTIONS)
    await state.set_state(AdminStates.set_plan_options)
    await callback.message.edit_text(
        f"📦 پلن‌های فعلی: <code>{current}</code>\n\n"
        "پلن‌های جدید را با کاما جدا کنید (مثال: 10,20,50,100):",
        reply_markup=admin_back_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AdminStates.set_plan_options, admin_filter)
async def on_set_plans(message: Message, session: AsyncSession, state) -> None:
    """ذخیره پلن‌ها."""
    if not message.text:
        return
    parts = [x.strip() for x in message.text.split(",")]
    if not all(p.isdigit() for p in parts):
        await message.answer("⚠️ فرمت: 10,20,50,100")
        return
    await set_setting(session, SETTING_PLAN_GB_OPTIONS, ",".join(parts))
    await state.clear()
    await message.answer("✅ پلن‌ها ذخیره شد.", reply_markup=admin_panel_kb())
