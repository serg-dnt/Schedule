import os
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.default import DefaultBotProperties
from doctor_bot.handlers.create_slots import router as create_router
from doctor_bot.handlers.view_slots import router as view_router
from doctor_bot.handlers.delete_slots import router as delete_router
from doctor_bot.handlers.view_appointments import router as appt_router
from doctor_bot.keyboards.main import main_menu_keyboard
from dotenv import load_dotenv
import asyncio

load_dotenv()

TELEGRAM_DOCTOR_TOKEN = os.getenv("DOCTOR_TELEGRAM_TOKEN")

bot = Bot(
    token=TELEGRAM_DOCTOR_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())
dp.include_routers(create_router, view_router, delete_router, appt_router)


@dp.message(F.text == "/start")
async def on_start(message: Message):
    await message.answer("Добро пожаловать!", reply_markup=main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "main_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню", reply_markup=main_menu_keyboard())

if __name__ == "__main__":
    print("🤖 DoctorBot запущен...")
    asyncio.run(dp.start_polling(bot))