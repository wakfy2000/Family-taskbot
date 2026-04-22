import logging
import time
import traceback
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import BOT_TOKEN
from database import init_db
from handlers.commands import start, help_command, task_command, list_command, my_command
from handlers.callbacks import button_handler
from handlers.jobs import check_overdue_tasks

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("task", task_command))
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("my", my_command))
    app.add_handler(CommandHandler("tasks", list_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_overdue_tasks, interval=300, first=10)
    else:
        logger.warning("JobQueue не установлен. Напоминания работать не будут. Установите: pip install 'python-telegram-bot[job-queue]'")

    print("=" * 60)
    print("СЕМЕЙНЫЙ БОТ ЗАПУЩЕН !")
    print("=" * 60)
    print("Редактирование, удаление, повтор, /my, напоминания")
    app.run_polling()


if __name__ == '__main__':
    while True:
        try:
            print("\nЗапуск бота...")
            main()
            print("Бот завершил работу")
        except KeyboardInterrupt:
            print("\nБот остановлен")
            break
        except Exception as e:
            print(f"\nОшибка: {e}")
            traceback.print_exc()
            print("\nПерезапуск через 10 секунд...")
            time.sleep(10)