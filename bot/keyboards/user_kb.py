"""کیبوردهای اینلاین کاربر."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.utils.helpers import format_price


def main_menu_kb(is_admin: bool = False) -> InlineKeyboardMarkup:
    """منوی اصلی."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 تست رایگان", callback_data="free_trial"),
        InlineKeyboardButton(text="🛒 خرید پلن", callback_data="buy_plan"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 اکانت من", callback_data="my_account"),
        InlineKeyboardButton(text="📖 راهنما", callback_data="help"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 پشتیبانی", callback_data="support"),
    )
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="⚙️ پنل ادمین", callback_data="admin_panel"),
        )
    return builder.as_markup()


def back_to_menu_kb() -> InlineKeyboardMarkup:
    """دکمه بازگشت."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_data="main_menu")]
        ]
    )


def plan_options_kb(plans: list[int], price_per_gb: int) -> InlineKeyboardMarkup:
    """انتخاب پلن گیگ."""
    builder = InlineKeyboardBuilder()
    for gb in plans:
        price = gb * price_per_gb
        builder.row(
            InlineKeyboardButton(
                text=f"📦 {gb} GB — {format_price(price)}",
                callback_data=f"select_plan:{gb}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu"))
    return builder.as_markup()


def payment_kb(gb: int) -> InlineKeyboardMarkup:
    """دکمه ارسال فیش."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 ارسال فیش پرداخت",
                    callback_data=f"send_receipt:{gb}",
                )
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="buy_plan")],
        ]
    )


def account_orders_kb(order_ids: list[int]) -> InlineKeyboardMarkup:
    """لیست اکانت‌های کاربر."""
    builder = InlineKeyboardBuilder()
    for oid in order_ids:
        builder.row(
            InlineKeyboardButton(
                text=f"📱 اکانت #{oid}",
                callback_data=f"order_detail:{oid}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu"))
    return builder.as_markup()


def order_detail_kb(order_id: int) -> InlineKeyboardMarkup:
    """جزئیات اکانت."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 دریافت Subscription",
                    callback_data=f"get_sub:{order_id}",
                )
            ],
            [InlineKeyboardButton(text="🔙 بازگشت", callback_data="my_account")],
        ]
    )
