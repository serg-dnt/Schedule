import os
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import requests
from dotenv import load_dotenv
from doctor_bot.keyboards.main import back_to_menu_button, main_menu_keyboard

load_dotenv()

BASE_API_URL = os.getenv("API_BASE_URL")

router = Router()

class ViewAppointmentsFSM(StatesGroup):
    selecting_date = State()
    selecting_to_cancel = State()

@router.callback_query(F.data == "Записи")
async def show_appointment_dates(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.get(f"{BASE_API_URL}/appointments/dates/", headers=headers)
    if response.status_code == 200:
        dates = sorted(response.json())
        if not dates:
            await callback.message.edit_text("Записей нет.", reply_markup=back_to_menu_button())
            return

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=date, callback_data=f"view_appts:{date}")]
                for date in dates
            ] + [[InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]]
        )
        await callback.message.answer("Выберите дату для просмотра записей:", reply_markup=keyboard)
        await state.set_state(ViewAppointmentsFSM.selecting_date)

@router.callback_query(F.data.startswith("view_appts:"))
async def list_appointments(callback: CallbackQuery, state: FSMContext):
    date = callback.data.split(":")[1]
    await state.update_data(date=date, cancel_list=[])
    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.get(f"{BASE_API_URL}/appointments/?date={date}", headers=headers)
    if response.status_code == 200:
        appointments = response.json()
        if not appointments:
            await callback.message.answer("На эту дату нет записей.")
            return

        text = ""
        buttons = []
        for appt in appointments:
            time = appt["start_datetime"][11:16]
            name = appt["patient"]["full_name"]
            phone = appt["patient"]["phone_number"]
            service = appt["service"]["name"]
            text += f"{time}\n{name}\n{phone}\n{service}\n\n"
            buttons.append([InlineKeyboardButton(text=f"Отменить запись на {time}", callback_data=f"cancel_appt:{appt['id']}")])

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=buttons + [
                [InlineKeyboardButton(text="✅ Подтвердить отмену", callback_data="confirm_cancellation")],
                [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
            ]
        )
        await callback.message.answer(text.strip(), reply_markup=keyboard)
        await state.set_state(ViewAppointmentsFSM.selecting_to_cancel)
    else:
        await callback.message.answer("Ошибка загрузки записей.")

@router.callback_query(F.data.startswith("cancel_appt:"))
async def toggle_cancel_appointment(callback: CallbackQuery, state: FSMContext):
    appt_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected = data.get("cancel_list", [])

    if appt_id in selected:
        selected.remove(appt_id)
    else:
        selected.append(appt_id)

    await state.update_data(cancel_list=selected)
    await callback.answer("Выбрано: " + ", ".join(map(str, selected)) or "Ничего не выбрано")

@router.callback_query(F.data == "confirm_cancellation")
async def confirm_cancel_appointments(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cancel_ids = data.get("cancel_list", [])
    if not cancel_ids:
        await callback.answer("Не выбраны записи.")
        return

    headers = {"X-Telegram-ID": str(callback.from_user.id)}
    response = requests.post(f"{BASE_API_URL}/appointments/cancel/", json={"appointment_ids": cancel_ids}, headers=headers)
    if response.status_code == 200:
        await callback.message.answer("Выбранные записи отменены ✅", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]]
        ))
    else:
        await callback.message.answer("Ошибка отмены записей.")
    await state.clear()

@router.callback_query(F.data == "back_to_menu")
async def back_to_main_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "Главное меню",
        reply_markup=main_menu_keyboard()
    )
