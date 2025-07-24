import os
from importlib.metadata import requires
import aiohttp

from dotenv import load_dotenv

from .utils import generate_slots

load_dotenv()

API_URL = os.getenv("API_BASE_URL")
DOCTOR_TOKEN = os.getenv("DOCTOR_JWT_ACCESS")

def get_auth_headers():
    return {"Authorization": f"Bearer {DOCTOR_TOKEN}"}

def create_slots(date_str, start_time_str, end_time_str):
    slots = generate_slots(date_str, start_time_str, end_time_str)
    data = {"slots": slots}

    response = requires.post(
        f"{API_URL}/slots/create",
        json=data,
        headers=get_auth_headers(),
    )
    return response.status_code == 201

async def get_doctor_slots(token: str, only_free: bool = False):
    url = f'{API_URL}/slots'
    params = {}
    if only_free:
        params["is_booked"] = "False"

    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                return await response.json()
        return []
