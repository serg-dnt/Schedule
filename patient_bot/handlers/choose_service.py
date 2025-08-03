# handlers/choose_service.py

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from patient_bot.states import AppointmentFSM
from patient_bot.utils.api import get_services, get_free_dates
from patient_bot.keyboards.inline import back_main_menu_keyboard, make_services_keyboard, make_dates_keyboard
from patient_bot.utils.logger import setup_logger


router = Router()
logger = setup_logger(__name__)


@router.callback_query(F.data == "choose_service")
async def choose_service(callback: CallbackQuery, state: FSMContext):
    await callback.answer()

    data = await state.get_data()
    doctor_id = data.get("doctor_id")
    telegram_id = callback.from_user.id

    if not doctor_id:
        logger.warning(f"User {telegram_id}: doctor_id missing in FSM state.")
        await callback.message.edit_text(
            "Ошибка: не выбран врач.",
            reply_markup=back_main_menu_keyboard("start_booking")
        )
        return

    services = get_services(telegram_id, doctor_id)

    if not services:
        logger.info(f"User {telegram_id}: No services found for doctor {doctor_id}.")
        await callback.message.edit_text(
            "У этого специалиста пока нет доступных услуг.",
            reply_markup=back_main_menu_keyboard("choose_doctor")
        )
        return

    logger.info(f"User {telegram_id}: Choosing service for doctor {doctor_id}.")
    await callback.message.edit_text(
        "Выберите услугу:",
        reply_markup=make_services_keyboard(services)
    )
    await state.set_state(AppointmentFSM.choosing_service)


@router.callback_query(AppointmentFSM.choosing_service)
async def service_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    service_id = int(callback.data.split(":")[-1])

    await state.update_data(service_id=service_id)
    data = await state.get_data()
    doctor_id = data.get("doctor_id")

    logger.info(f"User {telegram_id}: Selected service ID {service_id}.")

    try:
        # ✅ Получаем доступные даты от API
        dates = get_free_dates(telegram_id, doctor_id)

        if not dates:
            await callback.message.edit_text(
                "⚠️ Нет доступных дат для записи.",
                reply_markup=back_main_menu_keyboard("choose_service")
            )
            return

        await callback.message.edit_text(
            "Выберите дату:",
            reply_markup=make_dates_keyboard(dates)
        )
        await state.set_state(AppointmentFSM.choosing_date)

    except Exception as e:
        logger.exception("Ошибка при получении доступных дат")
        await callback.message.edit_text(
            "Произошла ошибка при получении дат.",
            reply_markup=back_main_menu_keyboard("choose_service")
        )