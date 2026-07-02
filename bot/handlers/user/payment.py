"""Handler پرداخت و ارسال فیش."""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.repository import (
    SETTING_PRICE_PER_GB,
    SETTING_SALES_ENABLED,
    create_payment,
    get_bool_setting,
    get_int_setting,
    get_or_create_user,
)
from bot.keyboards.admin_kb import payment_action_kb
from bot.keyboards.user_kb import back_to_menu_kb
from bot.states.states import PaymentStates
from bot.utils.helpers import format_price

logger = logging.getLogger(__name__)
router = Router(name="payment")


@router.callback_query(F.data.startswith("send_receipt:"))
async def cb_send_receipt(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    """شروع فرآیند ارسال فیش."""
    if not await get_bool_setting(session, SETTING_SALES_ENABLED):
        await callback.answer("فروش غیرفعال است.", show_alert=True)
        return

    gb = int(callback.data.split(":")[1])
    price_per_gb = await get_int_setting(session, SETTING_PRICE_PER_GB)
    total = gb * price_per_gb

    await state.set_state(PaymentStates.waiting_receipt)
    await state.update_data(gb=gb, amount=total)

    await callback.message.edit_text(
        f"📤 لطفاً <b>عکس فیش</b> پرداخت {format_price(total)} "
        f"برای پلن {gb} گیگ را ارسال کنید.\n\n"
        "⚠️ فقط عکس (نه فایل) ارسال کنید.",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(PaymentStates.waiting_receipt, F.photo)
async def on_receipt_photo(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """دریافت عکس فیش."""
    data = await state.get_data()
    gb = data.get("gb", 0)
    amount = data.get("amount", 0)

    if not gb or not amount:
        await message.answer("❌ خطا. لطفاً از منو دوباره شروع کنید.")
        await state.clear()
        return

    photo = message.photo[-1]
    user = message.from_user
    await get_or_create_user(session, user.id, user.username, user.full_name)

    payment = await create_payment(
        session,
        user_id=user.id,
        gb_amount=gb,
        amount=amount,
        receipt_file_id=photo.file_id,
    )
    await state.clear()

    await message.answer(
        "✅ فیش شما ثبت شد!\n\n"
        f"🆔 کد پیگیری: <b>#{payment.id}</b>\n"
        "پس از بررسی ادمین، کانفیگ برای شما ارسال می‌شود.",
        reply_markup=back_to_menu_kb(),
        parse_mode="HTML",
    )
    logger.info("فیش #%s از کاربر %s", payment.id, user.id)

    # اطلاع به ادمین‌ها
    admin_text = (
        f"🧾 <b>فیش جدید #{payment.id}</b>\n\n"
        f"👤 کاربر: {user.full_name} (@{user.username or '—'})\n"
        f"🆔 ID: <code>{user.id}</code>\n"
        f"📦 پلن: {gb} GB\n"
        f"💰 مبلغ: {format_price(amount)}"
    )
    for admin_id in settings.admin_ids:
        try:
            await bot.send_photo(
                admin_id,
                photo=photo.file_id,
                caption=admin_text,
                reply_markup=payment_action_kb(payment.id),
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("خطا در ارسال به ادمین %s", admin_id)


@router.message(PaymentStates.waiting_receipt)
async def on_receipt_invalid(message: Message) -> None:
    """فیش نامعتبر."""
    await message.answer("⚠️ لطفاً فقط عکس فیش را ارسال کنید.")
