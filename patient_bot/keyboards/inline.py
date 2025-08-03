from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Записаться на приём",
                                 callback_data="start_booking")
        ],
        [
            InlineKeyboardButton(text="📋 Мои записи",
                                 callback_data="view_appointments")
        ]
    ])

def back_main_menu_keyboard(back_callback: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data=back_callback
            ),
            InlineKeyboardButton(
                text="🏠 Главное меню",
                callback_data="main_menu"
            )
        ]
    ])

def make_services_keyboard(services: list):
    keyboard = []
    for service in services:
        keyboard.append([
            InlineKeyboardButton(
                text=service["name"],
                callback_data=f"service:{service['id']}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="choose_doctor"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def make_dates_keyboard(dates: list):
    keyboard = []
    for date_str in dates:
        keyboard.append([
            InlineKeyboardButton(
                text=datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y"),
                callback_data=f"date:{date_str}"
            )
        ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="choose_service"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def format_time(iso_string):
    dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
    return dt.strftime("%H:%M")

def make_times_keyboard(slots):
    buttons = []
    for slot in slots:
        time = slot["start_datetime"][11:16]
        callback_data = f"select_time:{slot['id']}"
        buttons.append(InlineKeyboardButton(text=time, callback_data=callback_data))

    # группируем по 2 кнопки в ряд
    keyboard = []
    row = []
    for i, btn in enumerate(buttons, start=1):
        row.append(btn)
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Добавляем кнопки "Назад" и "Главное меню"
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back:choose_date"),
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def confirm_appointment_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="choose_time"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ])

def generate_cancel_appointment_keyboard(appointment_id: int, selected: bool = False):
    text = f"{'✅' if selected else '❌'} Отменить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{text} запись {appointment_id}",
                    callback_data=f"toggle_cancel:{appointment_id}"
                )
            ],
            [
                InlineKeyboardButton(text="🔙 Назад",
                                     callback_data="choose_time"),
                InlineKeyboardButton(text="🏠 Главное меню",
                                     callback_data="main_menu")
            ]
        ]
    )

def cancel_appointments_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить отмену", callback_data="confirm_cancel")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]
        ]
    )

def main_menu_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="В меню", callback_data="main_menu")]
        ]
    )

def build_cancel_selection_keyboard(appointments, selected_ids=set()):
    keyboard = []

    for app in appointments:
        checked = "✅" if app["id"] in selected_ids else "☑️"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{checked} {app['start_datetime'][11:16]} — {app['service']['name']}",
                callback_data=f"toggle_cancel:{app['id']}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(text="✅ Подтвердить отмену", callback_data="confirm_cancel")
    ])
    keyboard.append([
        InlineKeyboardButton(text="⬅️ В меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)