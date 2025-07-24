import os

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from doctor_bot.keyboards.main import main_menu_keyboard, back_to_menu_button
import requests
# from datetime import datetime
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
    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.get(f"{BASE_API_URL}/slots/free_dates/", headers=headers)
    if response.status_code == 200:
        dates = sorted(set(response.json()))
        if not dates:
            await callback.message.edit_text("Нет доступных слотов для удаления.", reply_markup=back_to_menu_button())
            return
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=date, callback_data=f"del_date:{date}")]
                for date in dates
            ] + [[InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]]
        )
        await callback.message.edit_text("Выберите дату для удаления слотов:", reply_markup=keyboard)
        await state.set_state(DeleteSlotsFSM.selected_date)
    else:
        await callback.message.answer("Ошибка получения слотов.", reply_markup=back_to_menu_button())

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

    if slot_id in selected:
        selected.remove(slot_id)
    else:
        selected.append(slot_id)

    await state.update_data(selected_slots=selected)
    await callback.answer("Выбрано: " + ", ".join(map(str, selected)) or "Ничего не выбрано")

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