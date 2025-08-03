# handlers/confirm_appointment.py

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from patient_bot.states import AppointmentFSM
from patient_bot.utils.api import create_appointment, get_service_details
from patient_bot.keyboards.inline import confirm_appointment_keyboard, back_main_menu_keyboard
from patient_bot.utils.logger import setup_logger
from datetime import datetime

router = Router()
logger = setup_logger(__name__)


@router.callback_query(AppointmentFSM.confirming, F.data == "confirm")
async def confirm_appointment(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    telegram_id = callback.from_user.id

    doctor_id = data.get("doctor_id")
    service_id = data.get("service_id")
    date = data.get("selected_date")
    start_time = data.get("start_time")

    if not all([doctor_id, service_id, date, start_time]):
        logger.warning(f"User {telegram_id}: Missing data for confirmation.")
        await callback.message.edit_text(
            "Ошибка: не хватает данных для записи.",
            reply_markup=back_main_menu_keyboard("choose_time")
        )
        return

    logger.info(f"User {telegram_id}: Trying to book {date} at {start_time}")

    # Запрос к API на создание записи
    appointment = create_appointment(
        telegram_id=telegram_id,
        doctor_id=doctor_id,
        service_id=service_id,
        date=date,
        start_time=start_time
    )

    if appointment:
        doctor_name = appointment["doctor"]["full_name"]
        await callback.message.edit_text(
            f"✅ Вы успешно записались на приём!\n\n"
            f"👨‍⚕️ Специалист: {doctor_name}\n"
            f"📅 Дата: {datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")}\n"
            f"⏰ Время: {start_time}",
            reply_markup=back_main_menu_keyboard("main_menu")
        )
        await state.clear()
    else:
        await callback.message.edit_text(
            "Ошибка при создании записи. Попробуйте позже.",
            reply_markup=back_main_menu_keyboard("choose_time")
        )
