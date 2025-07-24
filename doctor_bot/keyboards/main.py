from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Создать слоты", callback_data="Создать слоты")],
            [InlineKeyboardButton(text="Просмотреть слоты", callback_data="Просмотреть слоты")],
            [InlineKeyboardButton(text="Удалить слоты", callback_data="Удалить слоты")],
            [InlineKeyboardButton(text="Записи", callback_data="Записи")],
        ]
    )

def create_date_keyboard(dates):
    buttons = [
        [InlineKeyboardButton(text=date, callback_data=date)]
        for date in dates
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_menu_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")]
    ])
