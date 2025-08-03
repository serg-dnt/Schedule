# handlers/choose_date.py

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from patient_bot.states import AppointmentFSM
from patient_bot.utils.api import get_free_dates, get_available_slots
from patient_bot.keyboards.inline import make_dates_keyboard, back_main_menu_keyboard, make_times_keyboard
from patient_bot.utils.logger import setup_logger

router = Router()
logger = setup_logger(__name__)


@router.callback_query(F.data == "choose_date")
async def choose_date(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    doctor_id = data.get("doctor_id")
    telegram_id = callback.from_user.id

    if not doctor_id:
        logger.warning(f"User {telegram_id}: doctor_id missing.")
        await callback.message.edit_text(
            "Ошибка: не выбран врач.",
            reply_markup=back_main_menu_keyboard("start_booking")
        )
        return

    free_dates = get_free_dates(telegram_id, doctor_id)
    if not free_dates:
        logger.info(f"User {telegram_id}: No free dates for doctor {doctor_id}.")
        await callback.message.edit_text(
            "Нет доступных дат для записи.",
            reply_markup=back_main_menu_keyboard("choose_service")
        )
        return

    logger.info(f"User {telegram_id}: Choosing date for doctor {doctor_id}.")
    await callback.message.edit_text(
        "Выберите дату:",
        reply_markup=make_dates_keyboard(free_dates)
    )


@router.callback_query(AppointmentFSM.choosing_date)
async def date_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    selected_date = callback.data.split(":")[-1]
    telegram_id = callback.from_user.id

    await state.update_data(selected_date=selected_date)
    data = await state.get_data()
    doctor_id = data.get("doctor_id")
    service_id = data.get("service_id")

    logger.info(f"User {telegram_id}: Selected date {selected_date}")

    # Получаем все подходящие слоты
    all_slots = get_available_slots(telegram_id, doctor_id, service_id)

    # Фильтруем по выбранной дате
    free_slots = [
        slot for slot in all_slots
        if slot["start_datetime"].startswith(selected_date)
    ]

    if not free_slots:
        await callback.message.edit_text(
            f"На {selected_date} нет свободного времени.",
            reply_markup=back_main_menu_keyboard("choose_date")
        )
        return

    await callback.message.edit_text(
        f"Свободное время на {selected_date}:",
        reply_markup=make_times_keyboard(free_slots)
    )
    await state.set_state(AppointmentFSM.choosing_time)