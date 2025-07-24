from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import requests
import os

from doctor_bot.keyboards.main import main_menu_keyboard, back_to_menu_button

router = Router()

class CreateSlotStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()


@router.callback_query(F.data == "Создать слоты")
async def create_slots_start(callback: CallbackQuery, state: FSMContext):
    text = "Введите дату в формате ДД.ММ.ГГГГ:"
    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_button()
    )
    await state.set_state(CreateSlotStates.waiting_for_date)


@router.message(CreateSlotStates.waiting_for_date)
async def receive_date(message: Message, state: FSMContext):
    try:
        date = datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        await state.update_data(date=str(date))
        await message.answer("Введите время начала смены (в формате ЧЧ:ММ):", reply_markup=back_to_menu_button())
        await state.set_state(CreateSlotStates.waiting_for_start_time)
    except ValueError:
        await message.answer("❗ Неверный формат даты. Введите в формате ДД.ММ.ГГГГ.", reply_markup=back_to_menu_button())


@router.message(CreateSlotStates.waiting_for_start_time)
async def receive_start_time(message: Message, state: FSMContext):
    try:
        time_start = datetime.strptime(message.text.strip(), "%H:%M").time()
    except ValueError:
        await message.answer("❗ Неверный формат времени. Введите в формате ЧЧ:ММ.", reply_markup=back_to_menu_button())
        return

    await state.update_data(start_time=time_start.strftime("%H:%M"))
    await message.answer("Введите время окончания смены (в формате ЧЧ:ММ):", reply_markup=back_to_menu_button())
    await state.set_state(CreateSlotStates.waiting_for_end_time)


@router.message(CreateSlotStates.waiting_for_end_time)
async def receive_end_time(message: Message, state: FSMContext):
    # Сначала только парсинг времени
    try:
        time_end = datetime.strptime(message.text.strip(), "%H:%M").time()
    except ValueError:
        await message.answer("❗ Неверный формат времени. Введите в формате ЧЧ:ММ.", reply_markup=back_to_menu_button())
        return

    data = await state.get_data()
    date = datetime.strptime(data["date"], "%Y-%m-%d").date()
    time_start = datetime.strptime(data["start_time"], "%H:%M").time()

    start_dt = datetime.combine(date, time_start)
    end_dt = datetime.combine(date, time_end)

    if end_dt <= start_dt:
        await message.answer("❗ Время окончания должно быть позже времени начала.", reply_markup=back_to_menu_button())
        return

    # Формируем слоты по 15 минут
    slots = []
    current = start_dt
    while current + timedelta(minutes=15) <= end_dt:
        slots.append({
            "start_datetime": current.isoformat(),
            "end_datetime": (current + timedelta(minutes=15)).isoformat()
        })
        current += timedelta(minutes=15)

    if not slots:
        await message.answer("❗ Нет доступных слотов в этом диапазоне.", reply_markup=back_to_menu_button())
        return

    # Отправка POST-запроса на API
    headers = {"X-Telegram-ID": str(message.from_user.id)}
    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/slots/create/",
            json={"slots": slots},
            headers=headers
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при отправке запроса: {e}", reply_markup=main_menu_keyboard())
        await state.clear()
        return

    if response.status_code == 201:
        await message.answer("✅ Слоты успешно созданы!", reply_markup=main_menu_keyboard())
    else:
        await message.answer(f"❌ Ошибка при создании слотов: {response.text}", reply_markup=main_menu_keyboard())

    await state.clear()