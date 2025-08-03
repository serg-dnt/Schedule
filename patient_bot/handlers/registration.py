from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from patient_bot.states import RegistrationFSM
from patient_bot.utils.api import register_user, check_user_exists
from patient_bot.keyboards.inline import back_main_menu_keyboard, main_menu_keyboard
from patient_bot.handlers.main import start_handler
from patient_bot.utils.logger import setup_logger
from aiogram.types import CallbackQuery

router = Router()
logger = setup_logger(__name__)


@router.message(F.text == "/start")
async def start_registration(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    logger.info(f"User {telegram_id} started bot")

    if check_user_exists(telegram_id):
        logger.info(f"User {telegram_id} already registered")
        await start_handler(message, state)  # ✅ Добавили state
        return

    await message.answer("Добро пожаловать! Для начала, введите ФИО:")
    await state.set_state(RegistrationFSM.waiting_for_full_name)


@router.message(RegistrationFSM.waiting_for_full_name)
async def get_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    await state.update_data(full_name=full_name)

    await message.answer("Введите ваш номер телефона (например, +79991234567):")
    await state.set_state(RegistrationFSM.waiting_for_phone)


@router.message(RegistrationFSM.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    phone_number = message.text.strip()
    data = await state.get_data()
    full_name = data.get("full_name")
    telegram_id = message.from_user.id

    logger.info(f"Registering user {telegram_id} with name '{full_name}' and phone '{phone_number}'")

    success = register_user(telegram_id, full_name, phone_number)

    if success:
        logger.info(f"User {telegram_id} successfully registered")
        await message.answer("✅ Вы успешно зарегистрированы!", reply_markup=main_menu_keyboard())

        # # Переход в главное меню
        # fake_callback = CallbackQuery(
        #     id="0",
        #     from_user=message.from_user,
        #     message=message,
        #     data="main_menu"
        # )
        # await start_handler(fake_callback, state)  # ✅ Добавили state

        await state.clear()
    else:
        logger.error(f"Registration failed for user {telegram_id}")
        await message.answer("❌ Ошибка при регистрации. Попробуйте позже.",
                             reply_markup=back_main_menu_keyboard("main_menu"))
        await state.clear()