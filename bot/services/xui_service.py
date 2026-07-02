"""سرویس اتصال به پنل 3x-ui با py3xui."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from py3xui import AsyncApi, Client

from bot.config import settings

logger = logging.getLogger(__name__)

# تبدیل گیگ به بایت (مطابق 3x-ui)
GB = 1024 * 1024 * 1024


class XUIService:
    """مدیریت کلاینت‌های VPN در پنل 3x-ui."""

    def __init__(self) -> None:
        self._api: AsyncApi | None = None

    async def _get_api(self) -> AsyncApi:
        """ایجاد اتصال API (lazy)."""
        if self._api is None:
            self._api = AsyncApi(
                host=settings.xui_host.rstrip("/"),
                token=settings.xui_token,
                use_tls_verify=settings.xui_use_tls_verify,
            )

            # فقط زمانی login انجام بده که Token وجود نداشته باشد.
            if not settings.xui_token:
                await self._api.login()

            logger.info("اتصال به پنل 3x-ui برقرار شد.")

        return self._api

    async def get_inbounds(self) -> list[dict]:
        """لیست inboundها."""
        api = await self._get_api()
        inbounds = await api.inbound.get_list()
        return [
            {
                "id": ib.id,
                "remark": ib.remark,
                "port": ib.port,
                "protocol": ib.protocol,
                "enable": ib.enable,
                "clients_count": len(ib.settings.clients) if ib.settings else 0,
            }
            for ib in inbounds
        ]

    @staticmethod
    def _generate_sub_id() -> str:
        """تولید شناسه subscription."""
        return secrets.token_hex(8)

    @staticmethod
    def _generate_email(user_id: int, prefix: str = "user") -> str:
        """ایمیل یکتا برای کلاینت."""
        ts = int(datetime.now(timezone.utc).timestamp())
        return f"{prefix}_{user_id}_{ts}@fazelino.lol"

    @staticmethod
    def _expiry_ms(days: int) -> int:
        """زمان انقضا به میلی‌ثانیه."""
        if days <= 0:
            return 0
        expire = datetime.now(timezone.utc) + timedelta(days=days)
        return int(expire.timestamp() * 1000)

    async def create_client(
        self,
        *,
        user_id: int,
        inbound_id: int,
        total_gb: float,
        days: int,
        is_trial: bool = False,
    ) -> dict:
        """
        ساخت کلاینت جدید در پنل.

        Returns:
            dict با کلیدهای email, uuid, sub_id, expires_at
        """
        api = await self._get_api()
        client_uuid = str(uuid.uuid4())
        sub_id = self._generate_sub_id()
        email = self._generate_email(user_id, prefix="trial" if is_trial else "user")

        new_client = Client(
            id=client_uuid,
            email=email,
            enable=True,
            limit_ip=2,
            total_gb=int(total_gb * GB),
            expiry_time=self._expiry_ms(days),
            tg_id=user_id,
            sub_id=sub_id,
        )

        await api.client.add(inbound_id, [new_client])
        logger.info(
            "کلاینت ساخته شد: email=%s inbound=%s gb=%s days=%s",
            email,
            inbound_id,
            total_gb,
            days,
        )

        expires_at = None
        if days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=days)

        return {
            "email": email,
            "uuid": client_uuid,
            "sub_id": sub_id,
            "expires_at": expires_at,
        }

    async def disable_client(self, inbound_id: int, client_uuid: str) -> None:
        """غیرفعال کردن کلاینت."""
        api = await self._get_api()
        client = await api.client.get_by_email(
            await self._get_email_by_uuid(inbound_id, client_uuid)
        )
        if client:
            client.enable = False
            client.id = client_uuid
            await api.client.update(client_uuid, client)
            logger.info("کلاینت غیرفعال شد: %s", client_uuid)

    async def _get_email_by_uuid(self, inbound_id: int, client_uuid: str) -> str:
        """یافتن email از uuid."""
        api = await self._get_api()
        inbound = await api.inbound.get_by_id(inbound_id)
        for c in inbound.settings.clients:
            if c.id == client_uuid:
                return c.email
        raise ValueError(f"کلاینت {client_uuid} یافت نشد.")

    async def get_client_stats(self, email: str) -> dict | None:
        """آمار ترافیک و وضعیت کلاینت."""
        api = await self._get_api()
        try:
            client = await api.client.get_by_email(email)
        except Exception:
            logger.exception("خطا در دریافت کلاینت: %s", email)
            return None

        if not client:
            return None

        used_bytes = (client.up or 0) + (client.down or 0)
        total_bytes = client.total_gb or 0
        remaining_bytes = max(total_bytes - used_bytes, 0)

        expiry_ms = client.expiry_time or 0
        expires_at = None
        if expiry_ms > 0:
            expires_at = datetime.fromtimestamp(expiry_ms / 1000, tz=timezone.utc)

        return {
            "email": client.email,
            "enabled": client.enable,
            "used_bytes": used_bytes,
            "total_bytes": total_bytes,
            "remaining_bytes": remaining_bytes,
            "expires_at": expires_at,
            "up": client.up or 0,
            "down": client.down or 0,
        }

    def build_subscription_url(self, sub_id: str) -> str:
        """ساخت لینک subscription."""
        base = settings.subscription_base_url.rstrip("/")
        return f"{base}/sub/{sub_id}"


# Singleton
xui_service = XUIService()
