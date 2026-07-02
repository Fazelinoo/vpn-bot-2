"""FSM States."""

from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    """وضعیت‌های فرآیند پرداخت."""

    waiting_receipt = State()


class AdminStates(StatesGroup):
    """وضعیت‌های پنل ادمین."""

    set_price = State()
    set_plan_options = State()
    set_inbound = State()
    search_user = State()
    reject_note = State()
