from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import os
import django

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Schedule.settings")
django.setup()

from booking.models import User


TELEGRAM_BOT_TOKEN = "ТОКЕН_ТВОЕГО_БОТА"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    user = User.objects.filter(telegram_id=telegram_id).first()

    if not user:
        await update.message.reply_text("Вы не зарегистрированы в системе.")
        return

    if not user.is_doctor or not user.is_doctor_approved:
        await update.message.reply_text(
            "Доступ запрещён. Вы не являетесь подтверждённым врачом."
        )
        return

    await update.message.reply_text(f"Здравствуйте, доктор {user.full_name}!")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Извините, я не понимаю эту команду.")

def run():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    print("Doctor bot is running...")
    app.run_polling()
