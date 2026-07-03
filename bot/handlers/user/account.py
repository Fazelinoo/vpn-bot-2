"""Handler اکانت کاربر."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import OrderStatus
from bot.database.repository import get_order, get_user_orders, parse_inbound_ids
from bot.keyboards.user_kb import account_orders_kb, back_to_menu_kb, order_detail_kb
from bot.services.qr_service import generate_qr_bytes
from bot.services.xui_service import xui_service
from bot.utils.helpers import format_bytes, format_datetime

logger = logging.getLogger(__name__)
router = Router(name="account")


@router.callback_query(F.data == "my_account")
async def cb_my_account(callback: CallbackQuery, session: AsyncSession) -> None:
    """لیست اکانت‌های کاربر."""
    orders = await get_user_orders(session, callback.from_user.id)
    if not orders:
        text = (
            "📭 شما هنوز اکانتی ندارید.\n"
            "از «تست رایگان» یا «خرید پلن» استفاده کنید."
        )
        try:
            await callback.message.edit_text(
                text,
                reply_markup=back_to_menu_kb(),
            )
        except Exception:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=back_to_menu_kb(),
            )
        await callback.answer()
        return

    order_ids = [o.id for o in orders]
    text = "📊 <b>اکانت‌های شما</b>\n\nیک اکانت را انتخاب کنید:"
    try:
        await callback.message.edit_text(
            text,
            reply_markup=account_orders_kb(order_ids),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.edit_caption(
            caption=text,
            reply_markup=account_orders_kb(order_ids),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("order_detail:"))
async def cb_order_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    """جزئیات اکانت."""
    order_id = int(callback.data.split(":")[1])
    order = await get_order(session, order_id)

    if not order or order.user_id != callback.from_user.id:
        await callback.answer("اکانت یافت نشد.", show_alert=True)
        return

    inbound_ids = parse_inbound_ids(order)
    stats = await xui_service.get_client_stats(order.client_email)
    text = await _format_order_text(order, stats, len(inbound_ids))

    await callback.message.edit_text(
        text,
        reply_markup=order_detail_kb(order.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("get_sub:"))
async def cb_get_sub(callback: CallbackQuery, session: AsyncSession) -> None:
    """ارسال subscription + QR."""
    order_id = int(callback.data.split(":")[1])
    order = await get_order(session, order_id)

    if not order or order.user_id != callback.from_user.id:
        await callback.answer("اکانت یافت نشد.", show_alert=True)
        return

    inbound_ids = parse_inbound_ids(order)
    sub_url = xui_service.build_subscription_url(order.sub_id)
    qr = generate_qr_bytes(sub_url)

    text = (
        f"🔗 <b>Subscription — اکانت #{order.id}</b>\n\n"
        f"📡 تعداد inbound: <b>{len(inbound_ids)}</b>\n\n"
        f"<code>{sub_url}</code>\n\n"
        "QR Code را اسکن کنید یا لینک را import کنید."
    )

    await callback.message.answer_photo(
        photo=BufferedInputFile(qr.read(), filename="qr.png"),
        caption=text,
        parse_mode="HTML",
    )
    await callback.answer("✅ ارسال شد")


async def _format_order_text(order, stats: dict | None, inbound_count: int = 1) -> str:
    """فرمت متن جزئیات اکانت."""
    status_map = {
        OrderStatus.ACTIVE: "🟢 فعال",
        OrderStatus.EXPIRED: "🔴 منقضی",
        OrderStatus.DISABLED: "⛔ متوقف",
        OrderStatus.PENDING: "⏳ در انتظار",
    }
    status = status_map.get(order.status, "❓")

    trial = " (تست رایگان)" if order.is_free_trial else ""
    lines = [
        f"📱 <b>اکانت #{order.id}{trial}</b>\n",
        f"📦 پلن: <b>{order.gb_amount} GB</b>",
        f"📡 تعداد inbound: <b>{inbound_count}</b>",
        f"📡 وضعیت: {status}",
    ]

    if stats:
        lines.append(f"📊 مصرف: <b>{format_bytes(stats['used_bytes'])}</b>")
        lines.append(f"💾 باقی‌مانده: <b>{format_bytes(stats['remaining_bytes'])}</b>")
        lines.append(f"📈 کل حجم: <b>{format_bytes(stats['total_bytes'])}</b>")
        panel_status = "🟢 فعال" if stats["enabled"] else "⛔ غیرفعال"
        lines.append(f"🔌 پنل: {panel_status}")

    expiry = stats["expires_at"] if stats and stats.get("expires_at") else order.expires_at
    lines.append(f"⏰ انقضا: <b>{format_datetime(expiry)}</b>")

    return "\n".join(lines)
