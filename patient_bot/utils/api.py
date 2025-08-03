# patient_bot/utils/api.py
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from patient_bot.utils.logger import setup_logger

load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL")
logger = setup_logger(__name__)

def get_doctors(telegram_id: int):
    url = f"{API_BASE_URL}/doctors/"
    headers = {"X-Telegram-ID": str(telegram_id)}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_services(telegram_id: int, doctor_id: int):
    url = f"{API_BASE_URL}/services/doctor/"
    headers = {"X-Telegram-ID": str(telegram_id)}
    params = {"doctor_id": doctor_id}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    return []

def get_free_dates(telegram_id: int, doctor_id: int):
    url = f"{API_BASE_URL}/slots/free_dates/"
    try:
        response = requests.get(url, params={"doctor_id": doctor_id})
        response.raise_for_status()
        return response.json().get("dates", [])
    except Exception as e:
        logger.error(f"[get_free_dates] User {telegram_id}: {e}")
        return []

def get_service_details(telegram_id: int, service_id: int):
    url = f"{API_BASE_URL}/services/{service_id}/"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[get_service_details] User {telegram_id}: {e}")
        return None

def get_available_slots(telegram_id: int, doctor_id: int, service_id: int):
    url = f"{API_BASE_URL}/slots/available/"
    try:
        response = requests.get(
            url, params={
                "doctor_id": doctor_id,
                # "date": date,
                "service_id": service_id
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[get_available_slots] User {telegram_id}: {e}")
        return []

def find_continuous_slots(slots: list, required_count: int):
    slots_sorted = sorted(slots)
    result = []

    def time_diff(t1, t2):
        fmt = "%H:%M"
        return (datetime.strptime(t2, fmt) - datetime.strptime(t1, fmt)) == timedelta(minutes=15)

    for i in range(len(slots_sorted) - required_count + 1):
        window = slots_sorted[i:i + required_count]
        valid = all(
            time_diff(window[j], window[j + 1])
            for j in range(len(window) - 1)
        )
        if valid:
            result.append(window[0])
    return result

def create_appointment(telegram_id: int, doctor_id: int, service_id: int,
                       date: str, start_time: str):
    url = f"{API_BASE_URL}/appointments/create/"

    # Собираем ISO-дату: "2025-07-30T14:00:00"
    try:
        start_datetime_str = f"{date} {start_time}"
        start_datetime = datetime.strptime(start_datetime_str, "%Y-%m-%d %H:%M")
        iso_datetime = start_datetime.isoformat()
    except ValueError as e:
        logger.error(f"[create_appointment] Invalid datetime format: {e}")
        return None

    payload = {
        "telegram_id": telegram_id,
        "doctor_id": doctor_id,
        "service_id": service_id,
        "start_datetime": iso_datetime
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[create_appointment] User {telegram_id}: {e}")
        return None


def get_user_appointments(telegram_id: int):
    url = f"{API_BASE_URL}/appointments/by-patient/"
    try:
        response = requests.post(url, json={"telegram_id": telegram_id})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[get_user_appointments] User {telegram_id}: {e}")
        return []

def cancel_appointments(telegram_id: int, appointment_ids: list):
    url = f"{API_BASE_URL}/appointments/cancel/"
    headers = {"X-Telegram-ID": str(telegram_id)}
    try:
        response = requests.post(
            url,
            json={
                "appointment_ids": appointment_ids
            },
            headers=headers
        )
        response.raise_for_status()
        return response.status_code == 200
    except Exception as e:
        logger.error(f"[cancel_appointments] User {telegram_id}: {e}")
        return False

def check_user_exists(telegram_id: int) -> bool:
    response = requests.get(f"{API_BASE_URL}/users/check/{telegram_id}/")
    return response.status_code == 200

def register_user(telegram_id: int, full_name: str, phone_number: str) -> bool:
    payload = {
        "telegram_id": telegram_id,
        "full_name": full_name,
        "phone_number": phone_number
    }
    response = requests.post(f"{API_BASE_URL}/users/register", json=payload)
    return response.status_code in [200, 201]

def get_slot_by_id(telegram_id: int, slot_id: int):
    url = f"{API_BASE_URL}/slots/{slot_id}/"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"[get_slot_by_id] User {telegram_id}: {e}")
        return None
