# doctor_bot/logger.py
import logging

logger = logging.getLogger("doctor_bot")
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)