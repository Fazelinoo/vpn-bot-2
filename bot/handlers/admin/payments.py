"""Handler ادمین — inbound و پرداخت‌ها."""

from __future__ import annotations

import logging
import random

from aiogram import Bot, F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.models import PaymentStatus
from bot.database.repository import (
    SETTING_PRICE_PER_GB,
    SETTING_SALE_INBOUNDS,
    approve_payment,
    create_order,
    disable_order,
    get_int_setting,
    get_order,
    get_payment,
    get_pending_payments,
    get_sale_inbounds,
    reject_payment,
    set_sale_inbounds,
)
from bot.filters.admin import AdminFilter
from bot.keyboards.admin_kb import (
    admin_back_kb,
    inbound_list_kb,
    payment_action_kb,
    pending_payments_kb,
)
from bot.keyboards.user_kb import order_detail_kb
from bot.services.qr_service import generate_qr_bytes
from bot.services.xui_service import xui_service
from bot.states.states import AdminStates
from bot.utils.helpers import format_price

logger = logging.getLogger(__name__)
router = Router(name="admin_payments")
admin_filter = AdminFilter()


@router.callback_query(F.data == "admin_inbound", admin_filter)
async def cb_admin_inbound(callback: CallbackQuery, session: AsyncSession) -> None:
    """لیست inboundها برای انتخاب چندگانه."""
    try:
        inbounds = await xui_service.get_inbounds()
        selected = await get_sale_inbounds(session)
        selected_text = ", ".join(map(str, selected)) if selected else "هیچ"
        await callback.message.edit_text(
            f"📡 <b>انتخاب Inbound برای فروش</b>\n\n"
            f"Inboundهای انتخاب شده: <b>{selected_text}</b>\n\n"
            "برای انتخاب/حذف روی هر inbound کلیک کنید:",
            reply_markup=inbound_list_kb(inbounds, selected),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.exception("خطا در دریافت inbound: %s", e)
        await callback.answer("خطا در اتصال به پنل.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_inbound:"), admin_filter)
async def cb_toggle_inbound(callback: CallbackQuery, session: AsyncSession) -> None:
    """افزودن/حذف inbound از لیست فروش."""
    inbound_id = int(callback.data.split(":")[1])
    selected = await get_sale_inbounds(session)
    
    if inbound_id in selected:
        selected.remove(inbound_id)
        await callback.answer(f"Inbound {inbound_id} حذف شد ❌", show_alert=True)
    else:
        selected.append(inbound_id)
        await callback.answer(f"Inbound {inbound_id} اضافه شد ✅", show_alert=True)
    
    await set_sale_inbounds(session, selected)
    await cb_admin_inbound(callback, session)


@router.callback_query(F.data == "admin_payments", admin_filter)
async def cb_admin_payments(callback: CallbackQuery, session: AsyncSession) -> None:
    """لیست فیش‌های در انتظار."""
    payments = await get_pending_payments(session)
    if not payments:
        await callback.message.edit_text(
            "✅ فیش در انتظاری وجود ندارد.",
            reply_markup=admin_back_kb(),
        )
    else:
        await callback.message.edit_text(
            f"🧾 <b>{len(payments)} فیش در انتظار</b>",
            reply_markup=pending_payments_kb(payments),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data.startswith("view_payment:"), admin_filter)
async def cb_view_payment(callback: CallbackQuery, session: AsyncSession) -> None:
    """مشاهده فیش."""
    payment_id = int(callback.data.split(":")[1])
    payment = await get_payment(session, payment_id)
    if not payment:
        await callback.answer("یافت نشد.", show_alert=True)
        return

    text = (
        f"🧾 <b>فیش #{payment.id}</b>\n\n"
        f"👤 کاربر: <code>{payment.user_id}</code>\n"
        f"📦 پلن: {payment.gb_amount} GB\n"
        f"💰 مبلغ: {format_price(payment.amount)}"
    )
    await callback.message.edit_text("🧾 در حال نمایش فیش...")
    await callback.bot.send_photo(
        callback.from_user.id,
        photo=payment.receipt_file_id,
        caption=text,
        reply_markup=payment_action_kb(payment.id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("approve_payment:"), admin_filter)
async def cb_approve_payment(
    callback: CallbackQuery, session: AsyncSession, bot: Bot
) -> None:
    """تایید فیش و ساخت کانفیگ."""
    payment_id = int(callback.data.split(":")[1])
    payment = await get_payment(session, payment_id)

    if not payment or payment.status != PaymentStatus.PENDING:
        await callback.answer("فیش نامعتبر.", show_alert=True)
        return

    await callback.answer("⏳ در حال ساخت کانفیگ...")

    try:
        sale_inbounds = await get_sale_inbounds(session)
        if not sale_inbounds:
            await callback.answer("هیچ inboundی برای فروش انتخاب نشده!", show_alert=True)
            return
        
        inbound_id = random.choice(sale_inbounds)
        client_data = await xui_service.create_client(
            user_id=payment.user_id,
            inbound_id=inbound_id,
            total_gb=payment.gb_amount,
            days=settings.default_plan_days,
        )

        order = await create_order(
            session,
            user_id=payment.user_id,
            gb_amount=payment.gb_amount,
            price=payment.amount,
            client_email=client_data["email"],
            client_uuid=client_data["uuid"],
            sub_id=client_data["sub_id"],
            inbound_id=inbound_id,
            expires_at=client_data["expires_at"],
        )
        await approve_payment(session, payment, order.id)

        sub_url = xui_service.build_subscription_url(client_data["sub_id"])
        qr = generate_qr_bytes(sub_url)

        user_text = (
            "✅ <b>پرداخت تایید شد!</b>\n\n"
            f"📦 پلن: <b>{payment.gb_amount} GB</b>\n"
            f"⏰ مدت: <b>{settings.default_plan_days} روز</b>\n\n"
            f"🔗 <b>Subscription:</b>\n<code>{sub_url}</code>"
        )
        await bot.send_photo(
            payment.user_id,
            photo=BufferedInputFile(qr.read(), filename="qr.png"),
            caption=user_text,
            reply_markup=order_detail_kb(order.id),
            parse_mode="HTML",
        )

        await callback.message.edit_caption(
            caption=f"✅ فیش #{payment.id} تایید شد — اکانت #{order.id}",
            reply_markup=admin_back_kb(),
        )
        logger.info("فیش #%s تایید شد", payment_id)

    except Exception as e:
        logger.exception("خطا در تایید فیش: %s", e)
        await callback.answer("خطا در ساخت کانفیگ!", show_alert=True)


@router.callback_query(F.data.startswith("reject_payment:"), admin_filter)
async def cb_reject_payment(callback: CallbackQuery, session: AsyncSession, state) -> None:
    """رد فیش."""
    payment_id = int(callback.data.split(":")[1])
    await state.set_state(AdminStates.reject_note)
    await state.update_data(payment_id=payment_id)
    await callback.message.edit_caption(
        caption="❌ دلیل رد (اختیاری) را ارسال کنید یا /skip بزنید:",
    )
    await callback.answer()


@router.message(AdminStates.reject_note, admin_filter)
async def on_reject_note(
    message: Message, session: AsyncSession, state, bot: Bot
) -> None:
    """ذخیره رد فیش."""
    data = await state.get_data()
    payment_id = data.get("payment_id")
    payment = await get_payment(session, payment_id)

    if not payment:
        await message.answer("فیش یافت نشد.")
        await state.clear()
        return

    note = "" if message.text == "/skip" else (message.text or "")
    await reject_payment(session, payment, note)
    await state.clear()

    text = f"❌ فیش #{payment.id} رد شد."
    if note:
        text += f"\nدلیل: {note}"
    await bot.send_message(payment.user_id, text)
    await message.answer("✅ رد شد.", reply_markup=admin_back_kb())
    logger.info("فیش #%s رد شد", payment_id)


@router.callback_query(F.data.startswith("disable_order:"), admin_filter)
async def cb_disable_order(callback: CallbackQuery, session: AsyncSession) -> None:
    """متوقف کردن اکانت."""
    order_id = int(callback.data.split(":")[1])
    order = await get_order(session, order_id)
    if not order:
        await callback.answer("یافت نشد.", show_alert=True)
        return

    try:
        await xui_service.disable_client(order.inbound_id, order.client_uuid)
        await disable_order(session, order)
        await callback.answer(f"اکانت #{order_id} متوقف شد ✅", show_alert=True)
        logger.info("اکانت #%s متوقف شد", order_id)
    except Exception as e:
        logger.exception("خطا در متوقف کردن: %s", e)
        await callback.answer("خطا!", show_alert=True)
