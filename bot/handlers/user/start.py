"""Handler شروع و منوی اصلی."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.repository import get_or_create_user
from bot.keyboards.user_kb import back_to_menu_kb, main_menu_kb
from bot.utils.helpers import is_admin

logger = logging.getLogger(__name__)
router = Router(name="start")

WELCOME_TEXT = """
🌐 <b>به فروشگاه VPN فازلینو خوش آمدید!</b>

🔐 سرویس VPN پرسرعت با دامنه <code>fazelino.lol</code>

<b>امکانات:</b>
🎁 تست رایگان ۱ گیگ / ۱ روز
🛒 خرید پلن بر اساس حجم (گیگ)
📱 لینک Subscription + QR Code
📊 مشاهده وضعیت اکانت

از منوی زیر گزینه مورد نظر را انتخاب کنید 👇
"""

HELP_TEXT = """
📖 <b>راهنمای استفاده</b>

<b>۱. تست رایگان</b>
هر ۲۴ ساعت یک‌بار ۱ گیگ برای ۱ روز دریافت کنید.

<b>۲. خرید پلن</b>
پلن دلخواه را انتخاب و مبلغ را کارت‌به‌کارت کنید.
سپس عکس فیش را ارسال کنید.

<b>۳. اتصال</b>
لینک Subscription را در برنامه‌های زیر import کنید:
• v2rayNG (اندروید)
• Streisand / V2Box (iOS)
• Hiddify / Nekoray (ویندوز/مک)

<b>۴. اکانت من</b>
مشاهده حجم باقی‌مانده، تاریخ انقضا و وضعیت.
"""


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    """دستور /start."""
    user = message.from_user
    if not user:
        return

    await get_or_create_user(
        session, user.id, user.username, user.full_name
    )
    logger.info("کاربر جدید/بازگشتی: %s (@%s)", user.id, user.username)

    admin = is_admin(user.id, settings.admin_ids)
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_kb(is_admin=admin),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, session: AsyncSession) -> None:
    """بازگشت به منوی اصلی."""
    user = callback.from_user
    admin = is_admin(user.id, settings.admin_ids)
    await callback.message.edit_text(
        WELCOME_TEXT,
        reply_markup=main_menu_kb(is_admin=admin),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery) -> None:
    """راهنما."""
    await callback.message.edit_text(
        HELP_TEXT,
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "support")
async def cb_support(callback: CallbackQuery) -> None:
    """پشتیبانی."""
    text = (
        "💬 <b>پشتیبانی</b>\n\n"
        "برای هرگونه سوال یا مشکل، پیام خود را همین‌جا ارسال کنید.\n"
        "تیم پشتیبانی در اسرع وقت پاسخ می‌دهد.\n\n"
        f"🌐 دامنه: <code>{settings.subscription_domain}</code>"
    )
    await callback.message.edit_text(
        text, reply_markup=back_to_menu_kb(), parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery) -> None:
    """بدون عملیات."""
    await callback.answer()
