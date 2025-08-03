from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from patient_bot.utils.api import get_user_appointments, cancel_appointments
from patient_bot.utils.logger import setup_logger
from patient_bot.states import AppointmentFSM
from .view_appointments import show_appointments
from ..keyboards.inline import main_menu_button

router = Router()
logger = setup_logger(__name__)


@router.callback_query(AppointmentFSM.viewing_appointments, F.data.startswith("toggle_cancel:"))
async def toggle_cancel(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split(":")[1])

    data = await state.get_data()
    selected_ids = set(data["selected_ids"])
    appointments = data["appointments"]

    if appointment_id in selected_ids:
        selected_ids.remove(appointment_id)
    else:
        selected_ids.add(appointment_id)

    await state.update_data(selected_ids=selected_ids)
    await show_appointments(callback, state)

@router.callback_query(AppointmentFSM.viewing_appointments, F.data == "confirm_cancel")
async def confirm_cancel(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_ids = list(data["selected_ids"])
    telegram_id = callback.from_user.id

    if not selected_ids:
        await callback.message.edit_text("Вы не выбрали записи.", reply_markup=main_menu_button())
        return

    success = cancel_appointments(telegram_id, selected_ids)

    if success:
        await callback.message.edit_text("✅ Записи отменены.", reply_markup=main_menu_button())
    else:
        await callback.message.edit_text("❌ Ошибка при отмене.", reply_markup=main_menu_button())

    await state.clear()