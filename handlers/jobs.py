import logging
from telegram.ext import ContextTypes
from database import get_overdue_tasks

logger = logging.getLogger(__name__)


async def check_overdue_tasks(context: ContextTypes.DEFAULT_TYPE):
    overdue = get_overdue_tasks()
    for chat_id, message_id, task_text, taken_by in overdue:
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"Напоминание: {taken_by}, вы взяли задачу «{task_text}» более 24 часов назад! Не забудьте выполнить.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке напоминания: {e}")