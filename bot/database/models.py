"""مدل‌های دیتابیس SQLAlchemy."""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base


class OrderStatus(str, enum.Enum):
    """وضعیت سفارش."""

    PENDING = "pending"
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class PaymentStatus(str, enum.Enum):
    """وضعیت پرداخت."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    """کاربر تلگرام."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram_id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    orders: Mapped[list[Order]] = relationship(back_populates="user")
    payments: Mapped[list[Payment]] = relationship(back_populates="user")
    free_tests: Mapped[list[FreeTest]] = relationship(back_populates="user")


class Order(Base):
    """سفارش / اکانت VPN."""

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    gb_amount: Mapped[float] = mapped_column(Float)
    price: Mapped[int] = mapped_column(Integer, default=0)
    client_email: Mapped[str] = mapped_column(String(128), unique=True)
    client_uuid: Mapped[str] = mapped_column(String(64))
    sub_id: Mapped[str] = mapped_column(String(32))
    inbound_ids: Mapped[str] = mapped_column(String(128))  # CSV of inbound IDs
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.ACTIVE
    )
    is_free_trial: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="orders")
    payment: Mapped[Payment | None] = relationship(back_populates="order")


class Payment(Base):
    """فیش پرداخت دستی."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=True
    )
    gb_amount: Mapped[float] = mapped_column(Float)
    amount: Mapped[int] = mapped_column(Integer)
    receipt_file_id: Mapped[str] = mapped_column(String(256))
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), default=PaymentStatus.PENDING
    )
    admin_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="payments")
    order: Mapped[Order | None] = relationship(back_populates="payment")


class Setting(Base):
    """تنظیمات داینامیک (قیمت، فروش، inbound و ...)."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text)


class FreeTest(Base):
    """ثبت تست‌های رایگان برای ضد اسپم."""

    __tablename__ = "free_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    order_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("orders.id"), nullable=True
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="free_tests")
