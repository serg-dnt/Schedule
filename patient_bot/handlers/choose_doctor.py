# patient_bot/handlers/choose_doctor.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from patient_bot.states import AppointmentFSM
from patient_bot.keyboards.inline import back_main_menu_keyboard
from patient_bot.utils.api import get_doctors
from patient_bot.utils.logger import setup_logger
from patient_bot.handlers.choose_service import choose_service

router = Router()
logger = setup_logger(__name__)

@router.callback_query(F.data == "start_booking")
async def handle_start_booking(callback: CallbackQuery, state: FSMContext):
    logger.info(f"👤 {callback.from_user.id} начал процесс записи.")
    await state.set_state(AppointmentFSM.choosing_doctor)

    try:
        doctors = get_doctors(callback.from_user.id)
        if not doctors:
            logger.warning("Список врачей пуст.")
            await callback.message.edit_text(
                "❗ Нет доступных врачей.",
                reply_markup=back_main_menu_keyboard("main_menu")
            )
            return

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=doctor["full_name"], callback_data=f"doctor:{doctor['id']}")]
                for doctor in doctors
            ] + back_main_menu_keyboard("main_menu").inline_keyboard
        )

        await callback.message.edit_text("Выберите врача 👨‍⚕️:", reply_markup=keyboard)

    except Exception as e:
        logger.exception("Ошибка при получении списка врачей")
        await callback.message.edit_text(
            "⚠️ Произошла ошибка при загрузке списка врачей.",
            reply_markup=back_main_menu_keyboard("main_menu")
        )


@router.callback_query(F.data.startswith("doctor:"))
async def doctor_selected(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id

    try:
        doctor_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        logger.warning(f"User {telegram_id}: некорректный doctor_id в callback_data: {callback.data}")
        await callback.message.edit_text(
            "Ошибка при выборе врача.",
            reply_markup=back_main_menu_keyboard("start_booking")
        )
        return

    # Получаем имя врача по callback_data из кнопок
    doctor_name = None
    for row in callback.message.reply_markup.inline_keyboard:
        for button in row:
            if button.callback_data == callback.data:
                doctor_name = button.text
                break
        if doctor_name:
            break

    await state.update_data(doctor_id=doctor_id, doctor_name=doctor_name)
    logger.info(f"User {telegram_id}: выбрал врача {doctor_id} ({doctor_name})")

    # Переход к выбору услуги
    await choose_service(callback, state)