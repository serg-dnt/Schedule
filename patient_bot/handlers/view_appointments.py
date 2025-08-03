from aiogram import Router, F
from aiogram.types import CallbackQuery
from patient_bot.keyboards.inline import build_cancel_selection_keyboard, \
    main_menu_button
from patient_bot.utils.api import get_user_appointments
from patient_bot.utils.logger import setup_logger
from aiogram.fsm.context import FSMContext
from patient_bot.states import AppointmentFSM
from datetime import datetime

router = Router()
logger = setup_logger(__name__)


@router.callback_query(F.data == "view_appointments")
async def view_appointments(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    appointments = get_user_appointments(telegram_id)

    if not appointments:
        await callback.message.edit_text("У вас пока нет записей.", reply_markup=main_menu_button())
        return

    await state.set_state(AppointmentFSM.viewing_appointments)
    await state.update_data(appointments=appointments, selected_ids=set())

    await show_appointments(callback, state)


async def show_appointments(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    appointments = data["appointments"]
    selected_ids = data["selected_ids"]

    text = generate_appointment_text(appointments, selected_ids)
    keyboard = build_cancel_selection_keyboard(appointments, selected_ids)

    await callback.message.edit_text(text, reply_markup=keyboard)


def generate_appointment_text(appointments, selected_ids):
    text = "📋 Ваши записи:\n\n"
    for app in appointments:
        dt_str = app["start_datetime"].replace("Z", "+0000")  # заменить Z на +0000 для UTC
        date = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")  # парсим с часовым поясом
        checked = "✅" if app["id"] in selected_ids else "☑️"
        text += (
            f"{checked}\n"
            f"⏰ Дата и время: {date.strftime('%d.%m.%Y %H:%M')}\n"
            f"💼 Услуга: {app['service']['name']}\n"
            f"🧑‍💼 Специалист: {app['doctor']['full_name']}\n\n\n"
        )
    return text.strip()