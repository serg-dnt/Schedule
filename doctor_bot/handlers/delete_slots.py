import os
from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from doctor_bot.keyboards.main import main_menu_keyboard, back_to_menu_button
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_API_URL = os.getenv("API_BASE_URL")

router = Router()

class DeleteSlotsFSM(StatesGroup):
    waiting_for_date = State()
    selected_date = State()
    selecting_slots = State()
    confirming_deletion = State()

@router.callback_query(F.data == "Удалить слоты")
async def delete_slots_start(callback: CallbackQuery, state: FSMContext):
    telegram_id = callback.from_user.id
    headers = {"X-Telegram-ID": str(telegram_id)}

    # Получаем информацию о враче (если API позволяет)
    try:
        doctor_resp = requests.get(f"{BASE_API_URL}/doctors/by_telegram/", headers=headers)
        doctor_resp.raise_for_status()
        doctor = doctor_resp.json()
        doctor_id = doctor["id"]
    except Exception as e:
        await callback.message.answer("Ошибка авторизации врача.", reply_markup=back_to_menu_button())
        return

    # Получаем свободные даты с учетом doctor_id
    try:
        response = requests.get(
            f"{BASE_API_URL}/slots/free_dates/",
            headers=headers,
            params={"doctor_id": doctor_id}
        )
        response.raise_for_status()
    except Exception as e:
        await callback.message.answer("Ошибка получения слотов.", reply_markup=back_to_menu_button())
        return

    dates = sorted(set(response.json().get("dates", [])))
    if not dates:
        await callback.message.edit_text("Нет доступных слотов для удаления.", reply_markup=back_to_menu_button())
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y"),
                callback_data=f"del_date:{date}"
            )]
            for date in dates
        ] + [[InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]]
    )

    await callback.message.edit_text("Выберите дату для удаления слотов:", reply_markup=keyboard)
    await state.set_state(DeleteSlotsFSM.selected_date)

@router.callback_query(F.data.startswith("del_date:"))
async def choose_slots_to_delete(callback: CallbackQuery, state: FSMContext):
    date = callback.data.split(":")[1]
    await state.update_data(date=date, selected_slots=[])
    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.get(f"{BASE_API_URL}/slots/?date={date}", headers=headers)
    if response.status_code == 200:
        slots = response.json()
        if not slots:
            await callback.message.answer("На эту дату нет свободных слотов.", reply_markup=back_to_menu_button())
            return

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=slot["start_datetime"][11:16], callback_data=f"toggle_slot:{slot['id']}")]
                for slot in slots
            ] + [[InlineKeyboardButton(text="✅ Удалить выбранные", callback_data="confirm_delete")],
                 [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]]
        )
        await callback.message.edit_text("Выберите слоты для удаления:", reply_markup=keyboard)
        await state.set_state(DeleteSlotsFSM.selecting_slots)
    else:
        await callback.message.edit_text("Ошибка загрузки слотов.", reply_markup=back_to_menu_button())

@router.callback_query(F.data.startswith("toggle_slot:"))
async def toggle_slot_selection(callback: CallbackQuery, state: FSMContext):
    slot_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("selected_slots", [])
    date = data.get("date")

    # Обновляем выбранные слоты
    if slot_id in selected:
        selected.remove(slot_id)
    else:
        selected.append(slot_id)
    await state.update_data(selected_slots=selected)

    # Загружаем все слоты на эту дату
    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.get(f"{BASE_API_URL}/slots/?date={date}", headers=headers)

    if response.status_code != 200:
        await callback.message.edit_text("Ошибка загрузки слотов.", reply_markup=back_to_menu_button())
        return

    slots = response.json()

    # Формируем клавиатуру со статусами ✅
    keyboard = []
    for slot in slots:
        slot_time = slot["start_datetime"][11:16]
        is_selected = slot["id"] in selected
        button_text = f"{'✅ ' if is_selected else ''}{slot_time}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"toggle_slot:{slot['id']}")])

    # Добавляем кнопки подтверждения и возврата
    keyboard.append([InlineKeyboardButton(text="✅ Удалить выбранные", callback_data="confirm_delete")])
    keyboard.append([InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")])

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    # Обновляем клавиатуру
    await callback.message.edit_reply_markup(reply_markup=markup)
    await callback.answer()

@router.callback_query(F.data == "confirm_delete")
async def confirm_delete_slots(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    slot_ids = data.get("selected_slots", [])
    if not slot_ids:
        await callback.answer("Выберите хотя бы один слот.")
        return

    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.delete(f"{BASE_API_URL}/slots/delete/", json={"slot_ids": slot_ids}, headers=headers)
    if response.status_code == 204:
        await callback.message.edit_text("Слоты удалены ✅", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]]
        ))
    else:
        await callback.message.edit_text("Ошибка удаления слотов.", reply_markup=back_to_menu_button())
    await state.clear()

@router.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=main_menu_keyboard()
    )