"""کیبوردهای اینلاین ادمین."""

from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_panel_kb() -> InlineKeyboardMarkup:
    """منوی پنل ادمین."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 آمار", callback_data="admin_stats"),
        InlineKeyboardButton(text="💰 قیمت هر گیگ", callback_data="admin_price"),
    )
    builder.row(
        InlineKeyboardButton(text="🛒 فروش", callback_data="admin_toggle_sales"),
        InlineKeyboardButton(text="🎁 تست رایگان", callback_data="admin_toggle_trial"),
    )
    builder.row(
        InlineKeyboardButton(text="📡 Inbound", callback_data="admin_inbound"),
        InlineKeyboardButton(text="📦 پلن‌ها", callback_data="admin_plans"),
    )
    builder.row(
        InlineKeyboardButton(text="🧾 فیش‌ها", callback_data="admin_payments"),
        InlineKeyboardButton(text="👥 کاربران", callback_data="admin_users"),
    )
    builder.row(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="main_menu"),
    )
    return builder.as_markup()


def admin_back_kb() -> InlineKeyboardMarkup:
    """بازگشت به پنل ادمین."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin_panel")]
        ]
    )


def payment_action_kb(payment_id: int) -> InlineKeyboardMarkup:
    """تایید/رد فیش."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تایید",
                    callback_data=f"approve_payment:{payment_id}",
                ),
                InlineKeyboardButton(
                    text="❌ رد",
                    callback_data=f"reject_payment:{payment_id}",
                ),
            ],
            [InlineKeyboardButton(text="🔙 لیست فیش‌ها", callback_data="admin_payments")],
        ]
    )


def pending_payments_kb(payments: list) -> InlineKeyboardMarkup:
    """لیست فیش‌های در انتظار."""
    builder = InlineKeyboardBuilder()
    for p in payments:
        builder.row(
            InlineKeyboardButton(
                text=f"🧾 #{p.id} — {p.gb_amount}GB — {p.amount:,}T",
                callback_data=f"view_payment:{p.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin_panel"))
    return builder.as_markup()


def users_list_kb(users: list, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """لیست کاربران با صفحه‌بندی."""
    builder = InlineKeyboardBuilder()
    for u in users:
        name = u.username or u.full_name or str(u.id)
        builder.row(
            InlineKeyboardButton(
                text=f"👤 {name} ({u.id})",
                callback_data=f"admin_user:{u.id}",
            )
        )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"admin_users_page:{page - 1}")
        )
    nav.append(
        InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop")
    )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(text="➡️", callback_data=f"admin_users_page:{page + 1}")
        )
    if nav:
        builder.row(*nav)

    builder.row(
        InlineKeyboardButton(text="🔍 جستجو", callback_data="admin_search_user"),
        InlineKeyboardButton(text="🔙 پنل", callback_data="admin_panel"),
    )
    return builder.as_markup()


def user_actions_kb(user_id: int, order_ids: list[int]) -> InlineKeyboardMarkup:
    """عملیات روی کاربر."""
    builder = InlineKeyboardBuilder()
    for oid in order_ids[:5]:
        builder.row(
            InlineKeyboardButton(
                text=f"⛔ متوقف #{oid}",
                callback_data=f"disable_order:{oid}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 کاربران", callback_data="admin_users"))
    return builder.as_markup()


def inbound_list_kb(inbounds: list[dict], selected_ids: list[int]) -> InlineKeyboardMarkup:
    """انتخاب چند inbound برای فروش."""
    builder = InlineKeyboardBuilder()
    for ib in inbounds:
        mark = "✅ " if ib["id"] in selected_ids else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{mark}{ib['remark']} (ID:{ib['id']}) — {ib['protocol']}:{ib['port']}",
                callback_data=f"toggle_inbound:{ib['id']}",
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 پنل ادمین", callback_data="admin_panel"))
    return builder.as_markup()
