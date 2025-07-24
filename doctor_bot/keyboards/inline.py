# # doctor_bot/keyboards/inline.py
# from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
#
# def main_menu_keyboard():
#     return InlineKeyboardMarkup(
#         keyboard=[
#             [InlineKeyboardButton(text="Создать слоты", callback_data="create_slots")],
#             [InlineKeyboardButton(text="Просмотреть слоты", callback_data="view_slots")],
#             [InlineKeyboardButton(text="Удалить слоты", callback_data="delete_slots")],
#             [InlineKeyboardButton(text="Записи", callback_data="view_appointments")],
#         ]
#     )
#
# def create_date_keyboard(dates):
#     buttons = [
#         [InlineKeyboardButton(text=date, callback_data=date)]
#         for date in dates
#     ]
#     return InlineKeyboardMarkup(inline_keyboard=buttons)
#
# def back_to_menu_button():
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="🔙 В меню", callback_data="back_to_menu")]
#     ])