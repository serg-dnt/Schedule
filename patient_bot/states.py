from aiogram.fsm.state import State, StatesGroup


class RegistrationFSM(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_phone = State()


class AppointmentFSM(StatesGroup):
    choosing_doctor = State()
    choosing_service = State()
    choosing_date = State()
    choosing_time = State()
    confirming = State()
    viewing_appointments = State()