import os
from dotenv import load_dotenv

load_dotenv()

YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_API_KEY = os.getenv("YOOKASSA_API_KEY")
MOY_NALOG_LOGIN = os.getenv("MOY_NALOG_LOGIN")
MOY_NALOG_PASSWORD = os.getenv("MOY_NALOG_PASSWORD")

STATE_FILE = "sync_state.json"
SYNC_START_DATE = os.getenv("SYNC_START_DATE")

INCOME_DESCRIPTION_TEMPLATE = os.getenv("INCOME_DESCRIPTION_TEMPLATE", "Платеж #{description}")

CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "0 */4 * * *")

def validate_config():
    required_vars = [
        ("YOOKASSA_SHOP_ID", YOOKASSA_SHOP_ID),
        ("YOOKASSA_API_KEY", YOOKASSA_API_KEY),
        ("MOY_NALOG_LOGIN", MOY_NALOG_LOGIN),
        ("MOY_NALOG_PASSWORD", MOY_NALOG_PASSWORD),
    ]
    
    missing = [var for var, val in required_vars if not val]
    if missing:
        raise ValueError(f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}")
    
    return True