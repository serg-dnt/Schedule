import asyncio
import logging
import os
import django
from telegram.ext import MessageHandler, filters
from datetime import datetime, timedelta

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from asgiref.sync import sync_to_async
from dotenv import load_dotenv

# ——— Загрузка .env
load_dotenv()
TOKEN = os.getenv("DOCTOR_TELEGRAM_TOKEN")

# ——— Настройка Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Schedule.settings")
django.setup()

from booking.models import User, AvailableSlot, Appointment

# ——— Логирование
logging.basicConfig(
    format="%(asctime)s – %(levelname)s – %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ——— ORM-хелперы
@sync_to_async
def get_doctor_by_telegram_id(tg_id):
    return User.objects.get(telegram_id=tg_id, is_doctor=True, is_doctor_approved=True)

@sync_to_async
def get_free_slot_dates(doctor):
    return list(
        AvailableSlot.objects.filter(doctor=doctor, is_booked=False)
        .order_by("start_datetime")
        .values_list("start_datetime__date", flat=True)
        .distinct()
    )

@sync_to_async
def get_free_slots_by_date(doctor, date):
    return list(
        AvailableSlot.objects.filter(
            doctor=doctor, is_booked=False, start_datetime__date=date
        ).order_by("start_datetime")
    )

@sync_to_async
def get_active_appointments_dates(doctor):
    return list(
        Appointment.objects.filter(doctor=doctor, status="active")
        .order_by("start_datetime")
        .values_list("start_datetime__date", flat=True)
        .distinct()
    )

@sync_to_async
def get_appointments_by_date(doctor, date):
    return list(
        Appointment.objects.filter(
            doctor=doctor, status="active", start_datetime__date=date
        ).select_related("patient", "service")
    )


# ——— Главное меню
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("➕ Создать слоты", callback_data="create_slots")],
        [InlineKeyboardButton("🗑 Удалить слоты", callback_data="delete_slots")],
        [InlineKeyboardButton("📅 Просмотреть слоты", callback_data="view_free_dates")],
        [InlineKeyboardButton("👥 Записи пациентов", callback_data="view_appointments")],
    ]
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("Выберите действие:", reply_markup=InlineKeyboardMarkup(kb))


# ——— /start
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await get_doctor_by_telegram_id(update.effective_user.id)
    except User.DoesNotExist:
        await update.message.reply_text("❌ Ваш Telegram ID не подтверждён как врач.")
        return
    await main_menu(update, context)


# ——— Просмотр свободных слотов
async def handle_view_free_dates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    doctor = await get_doctor_by_telegram_id(update.effective_user.id)
    dates = await get_free_slot_dates(doctor)
    if not dates:
        return await show_empty_with_back(
            update, "Свободных слотов нет."
        )
    kb = [
        [InlineKeyboardButton(d.isoformat(), callback_data=f"slots_{d.isoformat()}")]
        for d in dates
    ] + [[InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]]
    await update.callback_query.edit_message_text("📅 Выберите дату:", reply_markup=InlineKeyboardMarkup(kb))


async def handle_view_slots_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    doctor = await get_doctor_by_telegram_id(update.effective_user.id)
    date = datetime.fromisoformat(update.callback_query.data.replace("slots_", "")).date()
    slots = await get_free_slots_by_date(doctor, date)
    text = "🕒 " + "\n🕒 ".join(s.start_datetime.strftime("%H:%M") for s in slots) if slots else "Нет слотов на эту дату."
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]])
    )


# ——— Просмотр записей пациентов
async def handle_view_patient_appointments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    doctor = await get_doctor_by_telegram_id(update.effective_user.id)
    dates = await get_active_appointments_dates(doctor)
    if not dates:
        return await show_empty_with_back(
            update, "Нет активных записей пациентов."
        )
    kb = [
        [InlineKeyboardButton(d.isoformat(), callback_data=f"apps_{d.isoformat()}")]
        for d in dates
    ] + [[InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]]
    await update.callback_query.edit_message_text("📅 Выберите дату:", reply_markup=InlineKeyboardMarkup(kb))


async def handle_view_apps_by_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    doctor = await get_doctor_by_telegram_id(update.effective_user.id)
    date = datetime.fromisoformat(update.callback_query.data.replace("apps_", "")).date()
    apps = await get_appointments_by_date(doctor, date)
    lines = [f"{a.patient.full_name} – {a.service.name} @ {a.start_datetime.strftime('%H:%M')}" for a in apps]
    text = "👥 " + "\n👥 ".join(lines) if lines else "Нет записей."
    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]])
    )


# ——— Упрощённый показ сообщениий с кнопкой возврата
async def show_empty_with_back(update: Update, message: str):
    kb = [[InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")]]
    await update.callback_query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(kb))


# from telegram.ext import MessageHandler, filters
# from datetime import datetime, timedelta

# ——— Создание слотов — FSM логика
async def handle_create_slots_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    context.user_data["fsm"] = {"step": "date"}
    await update.callback_query.edit_message_text("📅 Введите дату в формате YYYY-MM-DD:")


# ——— Удаление слотов

@sync_to_async
def get_slot_by_id(slot_id):
    return AvailableSlot.objects.get(id=slot_id)


@sync_to_async
def get_slot_ids_by_date(doctor, date):
    return list(
        AvailableSlot.objects.filter(
            doctor=doctor, is_booked=False, start_datetime__date=date
        ).order_by("start_datetime").values_list("id", "start_datetime")
    )


@sync_to_async
def delete_slots_by_ids(ids):
    return AvailableSlot.objects.filter(id__in=ids).delete()


async def handle_delete_slots(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    doctor = await get_doctor_by_telegram_id(update.effective_user.id)
    dates = await get_free_slot_dates(doctor)
    if not dates:
        return await show_empty_with_back(update,
                                          "Нет доступных слотов для удаления.")
    kb = [
             [InlineKeyboardButton(d.isoformat(),
                                   callback_data=f"deldate_{d.isoformat()}")]
             for d in dates
         ] + [[InlineKeyboardButton("🔙 В главное меню",
                                    callback_data="main_menu")]]
    await update.callback_query.edit_message_text(
        "📅 Выберите дату для удаления слотов:",
        reply_markup=InlineKeyboardMarkup(kb))


async def handle_delete_slots_date(update: Update,
                                   context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    doctor = await get_doctor_by_telegram_id(update.effective_user.id)
    date_str = update.callback_query.data.replace("deldate_", "")
    date = datetime.fromisoformat(date_str).date()
    slots = await get_slot_ids_by_date(doctor, date)

    if not slots:
        return await show_empty_with_back(update,
                                          "Нет слотов на выбранную дату.")

    context.user_data["fsm_delete"] = {"date": date, "selected": set(),
                                       "all_slots": slots}

    # Строим клавиатуру сразу с пустыми отметками
    buttons = []
    for slot_id, dt in slots:
        label = f"🕒 {dt.strftime('%H:%M')}"
        buttons.append([InlineKeyboardButton(label,
                                             callback_data=f"toggleslot_{slot_id}")])
    buttons.append([InlineKeyboardButton("✅ Удалить выбранные",
                                         callback_data="confirm_delete_slots")])
    buttons.append(
        [InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")])

    await update.callback_query.edit_message_text(
        "Выберите слоты для удаления:",
        reply_markup=InlineKeyboardMarkup(buttons))


async def handle_toggle_slot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    slot_id = int(update.callback_query.data.replace("toggleslot_", ""))
    fsm = context.user_data.get("fsm_delete", {})
    selected = fsm.get("selected", set())
    all_slots = fsm.get("all_slots", [])

    if slot_id in selected:
        selected.remove(slot_id)
    else:
        selected.add(slot_id)

    fsm["selected"] = selected
    context.user_data["fsm_delete"] = fsm

    # Обновляем клавиатуру с учётом выделения
    buttons = []
    for sid, dt in all_slots:
        label = f"{'✅' if sid in selected else '🕒'} {dt.strftime('%H:%M')}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"toggleslot_{sid}")])
    buttons.append([InlineKeyboardButton("✅ Удалить выбранные", callback_data="confirm_delete_slots")])
    buttons.append([InlineKeyboardButton("🔙 В главное меню", callback_data="main_menu")])

    await update.callback_query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))


async def handle_confirm_delete(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    fsm = context.user_data.get("fsm_delete")
    if not fsm or not fsm.get("selected"):
        return await update.callback_query.edit_message_text(
            "❌ Вы не выбрали ни одного слота.")
    count = len(fsm["selected"])
    await delete_slots_by_ids(fsm["selected"])
    context.user_data.pop("fsm_delete", None)
    await update.callback_query.edit_message_text(f"✅ Удалено слотов: {count}")
    await main_menu(update, context)

async def handle_fsm_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fsm = context.user_data.get("fsm")
    if not fsm:
        return

    doctor = await get_doctor_by_telegram_id(update.effective_user.id)
    text = update.message.text.strip()

    if fsm["step"] == "date":
        try:
            date = datetime.strptime(text, "%Y-%m-%d").date()
            fsm["date"] = date
            fsm["step"] = "start_time"
            await update.message.reply_text("⏰ Введите время начала смены (например, 09:00):")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат даты. Повторите в формате YYYY-MM-DD.")

    elif fsm["step"] == "start_time":
        try:
            time_start = datetime.strptime(text, "%H:%M").time()
            fsm["start_time"] = time_start
            fsm["step"] = "end_time"
            await update.message.reply_text("⏰ Введите время окончания смены (например, 12:00):")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени. Повторите в формате HH:MM.")

    elif fsm["step"] == "end_time":
        try:
            time_end = datetime.strptime(text, "%H:%M").time()
            fsm["end_time"] = time_end

            # Формируем datetime
            date = fsm["date"]
            start_dt = datetime.combine(date, fsm["start_time"])
            end_dt = datetime.combine(date, time_end)

            if end_dt <= start_dt:
                await update.message.reply_text("❌ Время окончания должно быть позже начала.")
                return

            created = await create_slots_for_doctor(doctor, start_dt, end_dt)
            await update.message.reply_text(f"✅ Создано слотов: {created}")

            context.user_data.pop("fsm")
            await main_menu(update, context)

        except ValueError:
            await update.message.reply_text("❌ Неверный формат времени. Повторите в формате HH:MM.")


# ——— Логика создания слотов в БД
@sync_to_async
def create_slots_for_doctor(doctor, start_dt, end_dt, interval_minutes=15):
    count = 0
    current = start_dt
    while current + timedelta(minutes=interval_minutes) <= end_dt:
        slot_start = current
        slot_end = current + timedelta(minutes=interval_minutes)

        exists = AvailableSlot.objects.filter(
            doctor=doctor,
            start_datetime=slot_start
        ).exists()

        if not exists:
            AvailableSlot.objects.create(
                doctor=doctor,
                start_datetime=slot_start,
                end_datetime=slot_end
            )
            count += 1
        current = slot_end
    return count


# ——— Основной запуск
async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))

    app.add_handler(CallbackQueryHandler(handle_view_free_dates, pattern="^view_free_dates$"))
    app.add_handler(CallbackQueryHandler(handle_view_slots_by_date, pattern="^slots_"))

    app.add_handler(CallbackQueryHandler(handle_view_patient_appointments, pattern="^view_appointments$"))
    app.add_handler(CallbackQueryHandler(handle_view_apps_by_date, pattern="^apps_"))

    app.add_handler(CallbackQueryHandler(handle_create_slots_callback, pattern="^create_slots$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_fsm_input))

    app.add_handler(
        CallbackQueryHandler(handle_delete_slots, pattern="^delete_slots$"))
    app.add_handler(
        CallbackQueryHandler(handle_delete_slots_date, pattern="^deldate_"))
    app.add_handler(
        CallbackQueryHandler(handle_toggle_slot, pattern="^toggleslot_"))
    app.add_handler(CallbackQueryHandler(handle_confirm_delete,
                                         pattern="^confirm_delete_slots$"))

    logger.info("🤖 DoctorBot запущен.")
    await app.run_polling()

if __name__ == "__main__":
    # Запуск с корректной обработкой цикла
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
