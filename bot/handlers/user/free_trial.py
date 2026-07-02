"""Handler تست رایگان."""

from __future__ import annotations

import logging
import random

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.repository import (
    SETTING_SALE_INBOUNDS,
    add_order_client,
    can_use_free_trial,
    create_order,
    get_sale_inbounds,
    record_free_test,
)
from bot.keyboards.user_kb import back_to_menu_kb, order_detail_kb
from bot.services.qr_service import generate_qr_bytes
from bot.services.xui_service import xui_service

logger = logging.getLogger(__name__)
router = Router(name="free_trial")


@router.callback_query(F.data == "free_trial")
async def cb_free_trial(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    """درخواست تست رایگان."""
    user_id = callback.from_user.id
    allowed, reason = await can_use_free_trial(session, user_id)

    if not allowed:
        await callback.answer(reason, show_alert=True)
        return

    await callback.answer("⏳ در حال ساخت اکانت تست...")
    await callback.message.edit_text("⏳ لطفاً صبر کنید، اکانت تست در حال ساخت است...")

    try:
        sale_inbounds = await get_sale_inbounds(session)
        if not sale_inbounds:
            await callback.message.edit_text(
                "❌ خطا: هیچ inboundی برای فروش انتخاب نشده.",
                reply_markup=back_to_menu_kb(),
            )
            return
        
        # ایجاد سفارش بدون کانفیگ
        order = await create_order(
            session,
            user_id=user_id,
            gb_amount=settings.free_trial_gb,
            price=0,
            is_free_trial=True,
            expires_at=None,
        )
        
        # ساخت کانفیگ برای هر inbound انتخاب شده
        clients_data = []
        for inbound_id in sale_inbounds:
            client_data = await xui_service.create_client(
                user_id=user_id,
                inbound_id=inbound_id,
                total_gb=settings.free_trial_gb,
                days=settings.free_trial_days,
                is_trial=True,
            )
            await add_order_client(
                session,
                order_id=order.id,
                inbound_id=inbound_id,
                client_email=client_data["email"],
                client_uuid=client_data["uuid"],
                sub_id=client_data["sub_id"],
            )
            clients_data.append(client_data)
        
        await record_free_test(session, user_id, order.id)

        # ساخت پیام با تمام لینک‌های subscription
        text = (
            "🎁 <b>تست رایگان فعال شد!</b>\n\n"
            f"📦 حجم: <b>{settings.free_trial_gb} GB</b>\n"
            f"⏰ مدت: <b>{settings.free_trial_days} روز</b>\n"
            f"� تعداد کانفیگ: <b>{len(clients_data)}</b>\n\n"
        )
        
        for i, client_data in enumerate(clients_data, 1):
            sub_url = xui_service.build_subscription_url(client_data["sub_id"])
            text += f"🔗 <b>کانفیگ {i}:</b>\n<code>{sub_url}</code>\n\n"
        
        text += "QR Code را اسکن کنید یا لینک را کپی کنید."

        await callback.message.edit_text("✅ اکانت تست آماده شد!")
        
        # ارسال QR اولین کانفیگ
        first_qr = generate_qr_bytes(xui_service.build_subscription_url(clients_data[0]["sub_id"]))
        await bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(first_qr.read(), filename="qr.png"),
            caption=text,
            reply_markup=order_detail_kb(order.id),
            parse_mode="HTML",
        )
        logger.info("تست رایگان برای %s ساخته شد", user_id)

    except Exception as e:
        logger.exception("خطا در ساخت تست رایگان: %s", e)
        await callback.message.edit_text(
            "❌ خطا در ساخت اکانت. لطفاً بعداً تلاش کنید.",
            reply_markup=back_to_menu_kb(),
        )
