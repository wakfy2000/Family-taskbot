import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
DATABASE_FILE = "family_tasks.db"

URGENCY_ICONS = {
    "Не особо": "🟢",
    "Важная": "🔵",
    "Горит": "🔴"
}