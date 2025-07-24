# doctor_bot/handlers/view_slots.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import requests
from dotenv import load_dotenv
from datetime import datetime

from doctor_bot.keyboards.main import main_menu_keyboard, back_to_menu_button

load_dotenv()

router = Router()

@router.callback_query(F.data == "Просмотреть слоты")
async def handle_view_slots(callback: CallbackQuery):
    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.get("http://127.0.0.1:8000/api/slots/all/", headers=headers)

    if response.status_code != 200:
        await callback.message.edit_text("Не удалось получить список слотов ❌", reply_markup=back_to_menu_button())
        return

    slots = response.json()
    unique_dates = sorted(set(slot["start_datetime"][:10] for slot in slots))
    if not unique_dates:
        await callback.message.edit_text("Нет доступных слотов.", reply_markup=back_to_menu_button())
        return

    keyboard = [
        [InlineKeyboardButton(text=datetime.strptime(d, "%Y-%m-%d").strftime("%d.%m.%Y"), callback_data=f"view_slots:{d}")]
        for d in unique_dates
    ]
    keyboard.append([InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await callback.message.edit_text("Выберите дату для просмотра слотов:", reply_markup=markup)

@router.callback_query(F.data.startswith("view_slots:"))
async def handle_date_slots(callback: CallbackQuery):
    date_str = callback.data.split(":")[1]  # e.g., "2025-07-25"
    headers = {"X-Telegram-ID": str(callback.from_user.id)}

    try:
        # ВАЖНО: меняем на запрос всех слотов
        response = requests.get("http://127.0.0.1:8000/api/slots/all/", headers=headers)
        slots = response.json()
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при получении слотов: {e}")
        return

    # Фильтруем слоты по дате
    slots_on_date = [
        slot for slot in slots if slot["start_datetime"].startswith(date_str)
    ]

    if not slots_on_date:
        await callback.message.answer("❗ На эту дату нет доступных слотов.")
        return

    # Форматируем вывод
    text = f"🗓 Слоты на {date_str}:\n\n"
    for slot in slots_on_date:
        start_time = slot["start_datetime"][11:16]
        end_time = slot["end_datetime"][11:16]
        text += f"⏰ {start_time} - {end_time}\n"

    await callback.message.edit_text(
        text,
        reply_markup=back_to_menu_button()
    )

@router.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=main_menu_keyboard()
    )