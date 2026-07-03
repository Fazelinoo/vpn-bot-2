"""عملیات CRUD دیتابیس."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import settings
from bot.database.models import (
    FreeTest,
    Order,
    OrderStatus,
    Payment,
    PaymentStatus,
    Setting,
    User,
)

# کلیدهای تنظیمات
SETTING_PRICE_PER_GB = "price_per_gb"
SETTING_SALES_ENABLED = "sales_enabled"
SETTING_FREE_TRIAL_ENABLED = "free_trial_enabled"
SETTING_SALE_INBOUNDS = "sale_inbound_ids"
SETTING_PLAN_GB_OPTIONS = "plan_gb_options"

DEFAULT_SETTINGS: dict[str, str] = {
    SETTING_PRICE_PER_GB: "5000",
    SETTING_SALES_ENABLED: "true",
    SETTING_FREE_TRIAL_ENABLED: "true",
    SETTING_SALE_INBOUNDS: "1",
    SETTING_PLAN_GB_OPTIONS: "10,20,50,100",
}


async def ensure_default_settings(session: AsyncSession) -> None:
    """مقداردهی اولیه تنظیمات."""
    for key, value in DEFAULT_SETTINGS.items():
        existing = await session.get(Setting, key)
        if not existing:
            session.add(Setting(key=key, value=value))
    await session.commit()


async def get_setting(session: AsyncSession, key: str) -> str:
    """خواندن یک تنظیم."""
    row = await session.get(Setting, key)
    if row:
        return row.value
    return DEFAULT_SETTINGS.get(key, "")


async def set_setting(session: AsyncSession, key: str, value: str) -> None:
    """ذخیره تنظیم."""
    row = await session.get(Setting, key)
    if row:
        row.value = value
    else:
        session.add(Setting(key=key, value=value))
    await session.commit()


async def get_bool_setting(session: AsyncSession, key: str) -> bool:
    """خواندن تنظیم بولی."""
    return (await get_setting(session, key)).lower() == "true"


async def get_int_setting(session: AsyncSession, key: str) -> int:
    """خواندن تنظیم عددی."""
    return int(await get_setting(session, key))


async def get_plan_options(session: AsyncSession) -> list[int]:
    """لیست پلن‌های گیگ."""
    raw = await get_setting(session, SETTING_PLAN_GB_OPTIONS)
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


async def get_sale_inbounds(session: AsyncSession) -> list[int]:
    """لیست inboundهای فعال برای فروش."""
    raw = await get_setting(session, SETTING_SALE_INBOUNDS)
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]


async def set_sale_inbounds(session: AsyncSession, inbound_ids: list[int]) -> None:
    """ذخیره لیست inboundهای فعال برای فروش."""
    await set_setting(session, SETTING_SALE_INBOUNDS, ",".join(map(str, inbound_ids)))


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    username: str | None = None,
    full_name: str | None = None,
) -> User:
    """دریافت یا ایجاد کاربر."""
    user = await session.get(User, telegram_id)
    if user:
        if username and user.username != username:
            user.username = username
        if full_name and user.full_name != full_name:
            user.full_name = full_name
        await session.commit()
        return user

    user = User(id=telegram_id, username=username, full_name=full_name)
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def can_use_free_trial(session: AsyncSession, user_id: int) -> tuple[bool, str]:
    """بررسی امکان تست رایگان (کول‌داون ۲۴ ساعته)."""
    if not await get_bool_setting(session, SETTING_FREE_TRIAL_ENABLED):
        return False, "تست رایگان در حال حاضر غیرفعال است."

    cutoff = datetime.now(timezone.utc) - timedelta(
        hours=settings.free_trial_cooldown_hours
    )
    stmt = (
        select(FreeTest)
        .where(FreeTest.user_id == user_id, FreeTest.used_at >= cutoff)
        .order_by(FreeTest.used_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    last_test = result.scalar_one_or_none()

    if last_test:
        next_time = last_test.used_at + timedelta(
            hours=settings.free_trial_cooldown_hours
        )
        remaining = next_time - datetime.now(timezone.utc)
        hours = int(remaining.total_seconds() // 3600)
        minutes = int((remaining.total_seconds() % 3600) // 60)
        return False, f"⏳ {hours} ساعت و {minutes} دقیقه دیگر می‌توانید تست بگیرید."

    # فقط یک تست فعال همزمان
    active_trial = await session.execute(
        select(Order).where(
            Order.user_id == user_id,
            Order.is_free_trial.is_(True),
            Order.status == OrderStatus.ACTIVE,
        )
    )
    if active_trial.scalar_one_or_none():
        return False, "شما یک تست رایگان فعال دارید. ابتدا آن را مصرف کنید."

    return True, ""


async def record_free_test(
    session: AsyncSession, user_id: int, order_id: int
) -> None:
    """ثبت استفاده از تست رایگان."""
    session.add(FreeTest(user_id=user_id, order_id=order_id))
    await session.commit()


async def create_order(
    session: AsyncSession,
    *,
    user_id: int,
    gb_amount: float,
    price: int,
    client_email: str,
    client_uuid: str,
    sub_id: str,
    inbound_ids: list[int],
    is_free_trial: bool = False,
    expires_at: datetime | None = None,
) -> Order:
    """ایجاد سفارش جدید."""
    order = Order(
        user_id=user_id,
        gb_amount=gb_amount,
        price=price,
        client_email=client_email,
        client_uuid=client_uuid,
        sub_id=sub_id,
        inbound_ids=",".join(map(str, inbound_ids)),
        is_free_trial=is_free_trial,
        expires_at=expires_at,
        status=OrderStatus.ACTIVE,
    )
    session.add(order)
    await session.commit()
    await session.refresh(order)
    return order


def parse_inbound_ids(order: Order) -> list[int]:
    """استخراج لیست inbound IDs از سفارش."""
    if not order.inbound_ids:
        return []
    return [int(x) for x in order.inbound_ids.split(",") if x.strip()]


async def create_payment(
    session: AsyncSession,
    *,
    user_id: int,
    gb_amount: float,
    amount: int,
    receipt_file_id: str,
) -> Payment:
    """ثبت فیش پرداخت."""
    payment = Payment(
        user_id=user_id,
        gb_amount=gb_amount,
        amount=amount,
        receipt_file_id=receipt_file_id,
        status=PaymentStatus.PENDING,
    )
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def get_payment(session: AsyncSession, payment_id: int) -> Payment | None:
    """دریافت پرداخت."""
    return await session.get(Payment, payment_id)


async def get_pending_payments(session: AsyncSession) -> list[Payment]:
    """لیست فیش‌های در انتظار."""
    stmt = (
        select(Payment)
        .where(Payment.status == PaymentStatus.PENDING)
        .order_by(Payment.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def approve_payment(
    session: AsyncSession, payment: Payment, order_id: int
) -> None:
    """تایید پرداخت."""
    payment.status = PaymentStatus.APPROVED
    payment.order_id = order_id
    payment.processed_at = datetime.now(timezone.utc)
    await session.commit()


async def reject_payment(session: AsyncSession, payment: Payment, note: str = "") -> None:
    """رد پرداخت."""
    payment.status = PaymentStatus.REJECTED
    payment.admin_note = note
    payment.processed_at = datetime.now(timezone.utc)
    await session.commit()


async def get_user_orders(
    session: AsyncSession, user_id: int, active_only: bool = False
) -> list[Order]:
    """سفارش‌های کاربر."""
    stmt = select(Order).where(Order.user_id == user_id).order_by(Order.created_at.desc())
    if active_only:
        stmt = stmt.where(Order.status == OrderStatus.ACTIVE)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_order(session: AsyncSession, order_id: int) -> Order | None:
    """دریافت سفارش."""
    return await session.get(Order, order_id)


async def disable_order(session: AsyncSession, order: Order) -> None:
    """غیرفعال کردن سفارش."""
    order.status = OrderStatus.DISABLED
    await session.commit()


async def get_stats(session: AsyncSession) -> dict:
    """آمار کلی برای پنل ادمین."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_users = await session.scalar(select(func.count(User.id)))
    active_users = await session.scalar(
        select(func.count(func.distinct(Order.user_id))).where(
            Order.status == OrderStatus.ACTIVE
        )
    )

    today_sales = await session.scalar(
        select(func.count(Payment.id)).where(
            Payment.status == PaymentStatus.APPROVED,
            Payment.processed_at >= today_start,
        )
    )
    month_sales = await session.scalar(
        select(func.count(Payment.id)).where(
            Payment.status == PaymentStatus.APPROVED,
            Payment.processed_at >= month_start,
        )
    )
    total_revenue = await session.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.status == PaymentStatus.APPROVED
        )
    )
    pending_count = await session.scalar(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.PENDING)
    )

    return {
        "total_users": total_users or 0,
        "active_users": active_users or 0,
        "today_sales": today_sales or 0,
        "month_sales": month_sales or 0,
        "total_revenue": total_revenue or 0,
        "pending_payments": pending_count or 0,
    }


async def search_users(
    session: AsyncSession, query: str, limit: int = 20
) -> list[User]:
    """جستجوی کاربر با یوزرنیم یا آیدی."""
    stmt = select(User).order_by(User.created_at.desc()).limit(limit)
    if query.isdigit():
        stmt = stmt.where(User.id == int(query))
    elif query.startswith("@"):
        stmt = stmt.where(User.username.ilike(f"%{query[1:]}%"))
    else:
        stmt = stmt.where(
            or_(
                User.username.ilike(f"%{query}%"),
                User.full_name.ilike(f"%{query}%"),
            )
        )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_users(session: AsyncSession, offset: int = 0, limit: int = 15) -> list[User]:
    """لیست کاربران."""
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_users(session: AsyncSession) -> int:
    """تعداد کل کاربران."""
    return (await session.scalar(select(func.count(User.id)))) or 0
