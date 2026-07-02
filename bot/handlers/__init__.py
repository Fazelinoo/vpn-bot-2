"""Router setup."""

from aiogram import Router

from bot.handlers.admin.panel import router as admin_panel_router
from bot.handlers.admin.payments import router as admin_payments_router
from bot.handlers.admin.users import router as admin_users_router
from bot.handlers.user.account import router as account_router
from bot.handlers.user.free_trial import router as free_trial_router
from bot.handlers.user.payment import router as payment_router
from bot.handlers.user.purchase import router as purchase_router
from bot.handlers.user.start import router as start_router


def setup_routers() -> Router:
    """ثبت تمام routerها."""
    root = Router()
    root.include_router(start_router)
    root.include_router(free_trial_router)
    root.include_router(purchase_router)
    root.include_router(payment_router)
    root.include_router(account_router)
    root.include_router(admin_panel_router)
    root.include_router(admin_payments_router)
    root.include_router(admin_users_router)
    return root
