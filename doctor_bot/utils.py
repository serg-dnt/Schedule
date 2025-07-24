from datetime import datetime, timedelta

def generate_slots(date_str, start_time_str, end_time_str, interval_minutes=15):
    start_dt = datetime.strptime(f"{date_str} {start_time_str}", "%d.%m.%Y %H:%M")
    end_dt = datetime.strptime(f"{date_str} {end_time_str}", "%d.%m.%Y %H:%M")

    slots = []
    while start_dt + timedelta(minutes=interval_minutes) <= end_dt:
        slot_end = start_dt + timedelta(minutes=interval_minutes)
        slots.append({
            "start_datetime": start_dt.isoformat(),
            "end_datetime": slot_end.isoformat()
        })
        start_dt = slot_end
    return slots