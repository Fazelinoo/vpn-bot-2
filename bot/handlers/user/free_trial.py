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
        
        # ساخت کلاینت روی همه inboundها
        client_data = await xui_service.create_client(
            user_id=user_id,
            inbound_ids=sale_inbounds,
            total_gb=settings.free_trial_gb,
            days=settings.free_trial_days,
            is_trial=True,
        )
        
        order = await create_order(
            session,
            user_id=user_id,
            gb_amount=settings.free_trial_gb,
            price=0,
            client_email=client_data["email"],
            client_uuid=client_data["uuid"],
            sub_id=client_data["sub_id"],
            inbound_ids=sale_inbounds,
            is_free_trial=True,
            expires_at=client_data["expires_at"],
        )
        await record_free_test(session, user_id, order.id)

        sub_url = xui_service.build_subscription_url(client_data["sub_id"])
        qr = generate_qr_bytes(sub_url)

        text = (
            "🎁 <b>تست رایگان فعال شد!</b>\n\n"
            f"📦 حجم: <b>{settings.free_trial_gb} GB</b>\n"
            f"⏰ مدت: <b>{settings.free_trial_days} روز</b>\n"
            f"📡 تعداد inbound: <b>{len(sale_inbounds)}</b>\n\n"
            f"🔗 <b>Subscription:</b>\n<code>{sub_url}</code>\n\n"
            "QR Code را اسکن کنید یا لینک را کپی کنید."
        )

        await callback.message.edit_text("✅ اکانت تست آماده شد!")
        await bot.send_photo(
            callback.from_user.id,
            photo=BufferedInputFile(qr.read(), filename="qr.png"),
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
