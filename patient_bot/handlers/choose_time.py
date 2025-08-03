# handlers/choose_time.py

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from patient_bot.states import AppointmentFSM
from patient_bot.utils.api import get_available_slots, get_service_details, find_continuous_slots, get_slot_by_id
from patient_bot.keyboards.inline import make_times_keyboard, back_main_menu_keyboard, confirm_appointment_keyboard
from patient_bot.utils.logger import setup_logger
from datetime import datetime, timedelta

router = Router()
logger = setup_logger(__name__)


@router.callback_query(F.data == "choose_time")
async def choose_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    telegram_id = callback.from_user.id

    doctor_id = data.get("doctor_id")
    date = data.get("selected_date")
    service_id = data.get("service_id")

    if not (doctor_id and date and service_id):
        logger.warning(f"User {telegram_id}: Missing data for time selection.")
        await callback.message.edit_text(
            "Ошибка: недостающие данные.",
            reply_markup=back_main_menu_keyboard("choose_date")
        )
        return

    service = get_service_details(telegram_id, service_id)
    if not service:
        await callback.message.edit_text(
            "Ошибка при загрузке услуги.",
            reply_markup=back_main_menu_keyboard("choose_service")
        )
        return

    duration_minutes = service["duration_minutes"]
    required_slots = duration_minutes // 15

    all_slots = get_available_slots(telegram_id, doctor_id, date)
    if not all_slots:
        await callback.message.edit_text(
            "Нет доступного времени на эту дату.",
            reply_markup=back_main_menu_keyboard("choose_date")
        )
        return

    # Отфильтруем доступные окна
    available_times = find_continuous_slots(all_slots, required_slots)

    if not available_times:
        await callback.message.edit_text(
            "Недостаточно свободных слотов подряд для этой услуги.",
            reply_markup=back_main_menu_keyboard("choose_date")
        )
        return

    logger.info(f"User {telegram_id}: Choosing time for {date}, doctor {doctor_id}")
    await callback.message.edit_text(
        f"Выберите время:",
        reply_markup=make_times_keyboard(available_times)
    )
    await state.set_state(AppointmentFSM.confirming)


@router.callback_query(AppointmentFSM.choosing_time, F.data.startswith("select_time:"))
async def time_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    slot_id = int(callback.data.split(":")[-1])

    logger.info(f"User {telegram_id}: Selected slot ID {slot_id}")

    # Получим информацию о выбранном слоте (опционально, если нужно время отобразить)
    slot = get_slot_by_id(telegram_id, slot_id)
    if not slot:
        await callback.message.edit_text(
            "Произошла ошибка при получении слота.",
            reply_markup=confirm_appointment_keyboard()
        )
        return

    # Можно показать пользователю подтверждение:
    start_time = slot["start_datetime"][11:16]  # только время
    selected_date = slot["start_datetime"][:10]  # только дата

    # Сохраняем slot_id в состояние
    await state.update_data(
        slot_id=slot_id,
        start_time=start_time,
        selected_date=selected_date
    )

    await callback.message.edit_text(
        f"Вы выбрали {datetime.strptime(selected_date, "%Y-%m-%d").strftime("%d.%m.%Y")} в {start_time}.\nПодтвердить запись?",
        reply_markup=confirm_appointment_keyboard()
    )

    await state.set_state(AppointmentFSM.confirming)