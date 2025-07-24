# doctor_bot/states.py
from aiogram.fsm.state import StatesGroup, State

class CreateSlotStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_start = State()
    waiting_for_end = State()