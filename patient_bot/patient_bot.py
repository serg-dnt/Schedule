import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
# from patient_bot.config import TELEGRAM_PATIENT_BOT_TOKEN
# from patient_bot.middlewares import TelegramIDAuthMiddleware
from patient_bot.handlers import (
    registration,
    main,
    choose_doctor,
    choose_service,
    choose_date,
    choose_time,
    confirm_appointment,
    cancel_appointments,
    view_appointments
)
# from patient_bot.utils.api import cancel_appointments

load_dotenv()

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_PATIENT_BOT_TOKEN = os.getenv("USER_TELEGRAM_TOKEN")

# Запуск бота
async def main_runner():
    bot = Bot(token=TELEGRAM_PATIENT_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Подключение middlewares
    # dp.update.middleware(TelegramIDAuthMiddleware())

    # Регистрация хендлеров
    dp.include_routers(
        registration.router,
        main.router,
        choose_doctor.router,
        choose_service.router,
        choose_date.router,
        choose_time.router,
        confirm_appointment.router,
        view_appointments.router,
        cancel_appointments.router,
    )

    logger.info("Patient bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main_runner())