import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from patient_bot.keyboards.inline import main_menu_keyboard
from patient_bot.states import AppointmentFSM

from patient_bot.utils.logger import setup_logger

logger = setup_logger(__name__)
router = Router()

@router.message(F.text == "/start")
async def start_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пациент {user_id} запустил бота (/start)")
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать! Выберите действие:",
        reply_markup=main_menu_keyboard()
    )

@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    logger.info(f"Пациент {user_id} вернулся в главное меню")
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню:\nВыберите действие:",
        reply_markup=main_menu_keyboard()
    )