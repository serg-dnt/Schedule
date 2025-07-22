import os
import django
import asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from asgiref.sync import sync_to_async
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()
TOKEN = os.getenv("DOCTOR_TELEGRAM_TOKEN")

# Django настройки
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Schedule.settings')
django.setup()

from booking.models import User, AvailableSlot

# Conversation states
DATE, START_TIME, END_TIME, DELETE_DATE, SELECT_SLOTS_TO_DELETE = range(5)

user_state = {}

# ---------- ХЕНДЛЕРЫ ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    full_name = update.effective_user.full_name or ''
    username = update.effective_user.username or ''
    user, _ = await sync_to_async(User.objects.get_or_create)(
        telegram_id=telegram_id,
        defaults={
            'username': username,
            'full_name': full_name,
            'phone_number': '',
            'is_doctor': True,
            'is_doctor_approved': True,
        }
    )
    await update.message.reply_text(
        f"Добро пожаловать, доктор {user.full_name}!\n"
        "Доступные команды:\n"
        "/create_slots — создать слоты\n"
        "/delete_slots — удалить слоты"
    )


# ---------- СОЗДАНИЕ СЛОТОВ ----------

async def create_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите дату в формате ГГГГ-ММ-ДД:")
    return DATE

async def input_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['date'] = datetime.strptime(update.message.text, "%Y-%m-%d").date()
        await update.message.reply_text("Введите время начала (например, 09:00):")
        return START_TIME
    except ValueError:
        await update.message.reply_text("Неверный формат. Введите дату ГГГГ-ММ-ДД:")
        return DATE

async def input_start_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        start_time = datetime.strptime(update.message.text, "%H:%M").time()
        context.user_data['start_time'] = start_time
        await update.message.reply_text("Введите время окончания (например, 17:00):")
        return END_TIME
    except ValueError:
        await update.message.reply_text("Неверный формат времени. Введите время в формате ЧЧ:ММ")
        return START_TIME

async def input_end_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        end_time = datetime.strptime(update.message.text, "%H:%M").time()
        context.user_data['end_time'] = end_time
        doctor = await sync_to_async(User.objects.get)(telegram_id=update.effective_user.id)
        date = context.user_data['date']
        start_dt = datetime.combine(date, context.user_data['start_time'])
        end_dt = datetime.combine(date, end_time)

        slot_duration = timedelta(minutes=15)
        created = 0

        while start_dt + slot_duration <= end_dt:
            await sync_to_async(AvailableSlot.objects.get_or_create)(
                doctor=doctor,
                start_datetime=start_dt,
                end_datetime=start_dt + slot_duration
            )
            start_dt += slot_duration
            created += 1

        await update.message.reply_text(f"Создано {created} слотов на {date}")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")
        return END_TIME


# ---------- УДАЛЕНИЕ СЛОТОВ ----------

async def delete_slots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите дату (ГГГГ-ММ-ДД), чтобы просмотреть слоты:")
    return DELETE_DATE

async def input_delete_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        date = datetime.strptime(update.message.text, "%Y-%m-%d").date()
        doctor = await sync_to_async(User.objects.get)(telegram_id=update.effective_user.id)
        slots = await sync_to_async(list)(
            AvailableSlot.objects.filter(
                doctor=doctor,
                start_datetime__date=date
            ).order_by('start_datetime')
        )

        if not slots:
            await update.message.reply_text("Нет слотов на эту дату.")
            return ConversationHandler.END

        context.user_data['delete_slots'] = slots

        keyboard = [
            [InlineKeyboardButton(
                slot.start_datetime.strftime("%H:%M"),
                callback_data=str(slot.id)
            )]
            for slot in slots
        ]
        await update.message.reply_text(
            f"Выберите слот(ы) для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return SELECT_SLOTS_TO_DELETE

    except ValueError:
        await update.message.reply_text("Неверный формат даты. Попробуйте снова.")
        return DELETE_DATE


async def select_slots_to_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    slot_id = int(update.callback_query.data)
    await update.callback_query.answer()
    slot = await sync_to_async(AvailableSlot.objects.filter(id=slot_id).first)()
    if slot:
        await sync_to_async(slot.delete)()
        await update.callback_query.edit_message_text("Слот удалён.")
    else:
        await update.callback_query.edit_message_text("Слот не найден.")
    return ConversationHandler.END


# ---------- ОСНОВНАЯ ЛОГИКА ----------

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("create_slots", create_slots)],
        states={
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_date)],
            START_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_start_time)],
            END_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_end_time)],
        },
        fallbacks=[],
    ))

    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("delete_slots", delete_slots)],
        states={
            DELETE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_delete_date)],
            SELECT_SLOTS_TO_DELETE: [CallbackQueryHandler(select_slots_to_delete)],
        },
        fallbacks=[],
    ))

    print("🤖 DoctorBot запущен...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except RuntimeError:
        # В случае, если цикл уже работает (например, в PyCharm)
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
