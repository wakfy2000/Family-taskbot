import sqlite3
import logging
import re
import time
import traceback
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from dotenv import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def init_db():
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        message_id INTEGER,
        task_text TEXT,
        created_by TEXT,
        taken_by TEXT,
        created_at TEXT,
        status TEXT DEFAULT 'open',
        urgency TEXT DEFAULT 'Важная',
        repeat TEXT DEFAULT 'none',
        taken_at TEXT
    )
    ''')
    conn.commit()
    conn.close()
    logger.info("База данных готова")

def add_task(chat_id, message_id, task_text, created_by, urgency="Важная", repeat="none"):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO tasks (chat_id, message_id, task_text, created_by, created_at, urgency, repeat) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (chat_id, message_id, task_text, created_by, datetime.now().isoformat(), urgency, repeat)
    )
    conn.commit()
    conn.close()
    logger.info(f"Задача добавлена: '{task_text[:50]}...'")

def take_task(message_id, taken_by):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE tasks SET taken_by = ?, status = "taken", taken_at = ? WHERE message_id = ?',
        (taken_by, datetime.now().isoformat(), message_id)
    )
    conn.commit()
    conn.close()
    logger.info(f"Задача взята пользователем: {taken_by}")

def mark_task_done(message_id):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE tasks SET status = "done" WHERE message_id = ?',
        (message_id,)
    )
    conn.commit()
    conn.close()
    logger.info(f"Задача отмечена как выполненная, message_id: {message_id}")

def get_task_by_message(message_id):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT * FROM tasks WHERE message_id = ?',
        (message_id,)
    )
    task = cursor.fetchone()
    conn.close()
    return task

def get_chat_tasks(chat_id):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT task_text, created_by, taken_by, status, urgency, repeat FROM tasks WHERE chat_id = ? ORDER BY created_at DESC',
        (chat_id,)
    )
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def get_user_tasks(chat_id, username):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT task_text, created_by, taken_by, status, urgency, repeat FROM tasks WHERE chat_id = ? AND taken_by = ? ORDER BY created_at DESC',
        (chat_id, username)
    )
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def delete_task(message_id):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM tasks WHERE message_id = ?', (message_id,))
    conn.commit()
    conn.close()
    logger.info(f"Задача удалена, message_id: {message_id}")

def update_task_text(message_id, new_text):
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE tasks SET task_text = ? WHERE message_id = ?', (new_text, message_id))
    conn.commit()
    conn.close()
    logger.info(f"Текст задачи обновлён, message_id: {message_id}")

def get_overdue_tasks():
    conn = sqlite3.connect('family_tasks.db')
    cursor = conn.cursor()
    threshold = (datetime.now() - timedelta(hours=24)).isoformat()
    cursor.execute(
        'SELECT chat_id, message_id, task_text, taken_by FROM tasks WHERE status = "taken" AND taken_at IS NOT NULL AND taken_at < ?',
        (threshold,)
    )
    tasks = cursor.fetchall()
    conn.close()
    return tasks

#Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """
     **FamilyTaskBot** — семейный органайзер!

     **Команды:**
    /task [что сделать] — создать задачу
    /list — все задачи
    /my — только мои задачи
    /help — подробнее
    """
    if update.effective_chat.type in ["group", "supergroup"]:
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    else:
        await update.message.reply_text("Добавьте меня в групповой чат семьи!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    **FamilyTaskBot — Помощь**

    **Основные команды:**
    /task [текст] — создать задачу
    /list — показать все задачи
    /my — показать только мои задачи

    **Срочность:** Не особо ,Важная ,Горит 
    **Повтор:** добавьте в конец задачи:
        «каждый день», «каждую неделю», «каждый месяц»

    **Управление задачей:** (видны только создателю)
    Удалить — удалить задачу

    **Напоминания:** если задача не выполнена более 24ч, бот напомнит в чате.
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Добавьте меня в группу семьи!")
        return

    if not context.args:
        await update.message.reply_text(
            "Напишите что сделать!\n"
            "Пример: `/task купить хлеб`\n"
            "Пример: `/task вынести мусор каждый день`\n"
            "💡 Уровни срочности:\n"
            "`Не особо` ,`Важная` ,`Горит` ",
            parse_mode='Markdown'
        )
        return

  
    urgency = "Важная"
    repeat = "none"
    task_parts = " ".join(context.args)

    if task_parts.lower().endswith(" горит"):
        urgency = "Горит"
        task_text = task_parts[:-6]
    elif task_parts.lower().endswith(" не особо"):
        urgency = "Не особо"
        task_text = task_parts[:-9]
    else:
        task_text = task_parts

    repeat_patterns = {
        r'\bкаждый день\b': 'daily',
        r'\bкаждую неделю\b': 'weekly',
        r'\bкаждый месяц\b': 'monthly'
    }
    for pattern, rep in repeat_patterns.items():
        if re.search(pattern, task_text, re.IGNORECASE):
            repeat = rep
            task_text = re.sub(pattern, '', task_text, flags=re.IGNORECASE).strip()
            break

    user = update.effective_user

    urgency_icons = {"Не особо", "Важная", "Горит"}
    icon = urgency_icons.get(urgency)


    message = await update.effective_chat.send_message(
        f"{icon} **Новая задача от {user.full_name}:**\n"
        f"📋 {task_text}\n\n"
        f"⚡ Срочность: **{urgency}**\n"
        f"🔁 Повтор: **{repeat if repeat != 'none' else 'нет'}**\n"
        f"👤 Кто сделает?",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Я сделаю!", callback_data="take_task")
        ]])
    )

    # Сохраняем в базу данных
    add_task(
        chat_id=update.effective_chat.id,
        message_id=message.message_id,
        task_text=task_text,
        created_by=user.full_name,
        urgency=urgency,
        repeat=repeat
    )

    # Добавляем кнопки редактирования/удаления (только для создателя)
    new_keyboard = [
        [InlineKeyboardButton("Я сделаю!", callback_data="take_task")],
        [
            InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{message.message_id}")
        ]
    ]
    await message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))

    try:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"Вы создали задачу: {task_text}\n"
                 f"Срочность: {urgency}\n"
                 f"Повтор: {repeat}\n"
                 f"Ожидайте исполнителя.",
            parse_mode='Markdown'
        )
    except:
        logger.warning("Не удалось отправить личное уведомление создателю")

    try:
        await update.message.delete()
    except:
        pass

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Эта команда работает только в группах!")
        return

    tasks = get_chat_tasks(update.effective_chat.id)
    if not tasks:
        await update.message.reply_text("Пока нет задач!")
        return

    urgency_icons = {"Не особо", "Важная", "Горит"}
    open_tasks, taken_tasks, done_tasks = [], [], []
    for task_text, created_by, taken_by, status, urgency, repeat in tasks:
        if status == 'done':
            done_tasks.append((task_text, created_by, taken_by, urgency, repeat))
        elif status == 'taken':
            taken_tasks.append((task_text, created_by, taken_by, urgency, repeat))
        else:
            open_tasks.append((task_text, created_by, taken_by, urgency, repeat))

    message_text = "**Семейные задачи:**\n\n"
    if open_tasks:
        message_text += "**Ищут исполнителя:**\n"
        for task_text, created_by, _, urgency, repeat in open_tasks:
            icon = urgency_icons.get(urgency,)
            repeat_str = f" {repeat}" if repeat != 'none' else ''
            message_text += f"{icon} {task_text}\n  👤Создал: {created_by} | {urgency}{repeat_str}\n\n"
    if taken_tasks:
        message_text += " **В работе:**\n"
        for task_text, created_by, taken_by, urgency, repeat in taken_tasks:
            icon = urgency_icons.get(urgency, )
            repeat_str = f" {repeat}" if repeat != 'none' else ''
            message_text += f"{icon} {task_text}\n {created_by} → {taken_by} | {urgency}{repeat_str}\n\n"
    if done_tasks:
        message_text += "**Выполнено:**\n"
        for task_text, created_by, taken_by, urgency, repeat in done_tasks:
        
            message_text += f"{task_text}\n  {created_by} → {taken_by}\n\n"
    await update.message.reply_text(message_text, parse_mode='Markdown')

async def my_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Эта команда работает только в группах!")
        return

    user = update.effective_user
    tasks = get_user_tasks(update.effective_chat.id, user.full_name)
    if not tasks:
        await update.message.reply_text("У вас нет активных задач!")
        return

    urgency_icons = {"Не особо", "Важная", "Горит"}
    taken_tasks, done_tasks = [], []
    for task_text, created_by, taken_by, status, urgency, repeat in tasks:
        if status == 'done':
            done_tasks.append((task_text, created_by, urgency, repeat))
        else:
            taken_tasks.append((task_text, created_by, urgency, repeat))

    message_text = f"**Задачи для {user.full_name}:**\n\n"
    if taken_tasks:
        message_text += "**В работе:**\n"
        for task_text, created_by, urgency, repeat in taken_tasks:
            icon = urgency_icons.get(urgency)
            repeat_str = f"{repeat}" if repeat != 'none' else ''
            message_text += f"{icon} {task_text}\n  от {created_by} | {urgency}{repeat_str}\n\n"
    if done_tasks:
        message_text += "**Выполнено:**\n"
        for task_text, created_by, urgency, repeat in done_tasks:
            message_text += f" {task_text}\n от {created_by}\n\n"
    await update.message.reply_text(message_text, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = query.data
    if data.startswith('delete_'):
        task_message_id = int(data.split('_')[1])
        task = get_task_by_message(task_message_id)
        if not task:
            await query.edit_message_text("Задача не найдена!")
            return
        if task[4] != user.full_name:
            await query.answer("Только создатель может удалить!", show_alert=True)
            return
        delete_task(task_message_id)
        await query.edit_message_text(
            text="🗑 Задача удалена.",
            parse_mode='Markdown'
        )
        return

    if data == "take_task":
        message_id = query.message.message_id
        task = get_task_by_message(message_id)
        if not task:
            await query.edit_message_text(" Задача не найдена!")
            return
        task_id, chat_id, msg_id, task_text, created_by, taken_by, created_at, status, urgency, repeat, taken_at = task
        if taken_by:
            await query.edit_message_text(
                text=query.message.text + f"\n\nЗадача уже взята: {taken_by}",
                parse_mode='Markdown'
            )
            return

        take_task(message_id, user.full_name)
        urgency_icons = {"Не особо", "Важная", "Горит"}
        icon = urgency_icons.get(urgency)
        new_text = f"{icon} **Задача от {created_by}:**\n"
        new_text += f"{task_text}\n\n"
        new_text += f"Срочность: **{urgency}**\n"
        if repeat != 'none':
            new_text += f"Повтор: **{repeat}**\n"
        new_text += f"**Взял(а): {user.full_name}**\n"
        new_text += f"Взято: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        await query.edit_message_text(text=new_text, parse_mode='Markdown')
        try:
            await context.bot.send_message(
                chat_id=update.effective_user.id,
                text=f" Вы взяли задачу: {task_text}\nСрочность: {urgency}\n Создатель: {created_by}",
                parse_mode='Markdown'
            )
        except:
            logger.warning("Не удалось отправить личное уведомление исполнителю")

        # Кнопка выполнения
        await query.message.reply_text(
            f"Отлично, {user.full_name}!\n"
            f"{task_text}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(" Задача выполнена", callback_data=f"complete_{message_id}")
            ]])
        )
        return

    if data.startswith('complete_'):
        task_message_id = int(data.split('_')[1])
        task = get_task_by_message(task_message_id)
        if not task:
            await query.answer("Задача не найдена!", show_alert=True)
            return
        task_id, chat_id, msg_id, task_text, created_by, taken_by, created_at, status, urgency, repeat, taken_at = task
        if taken_by != user.full_name:
            await query.answer(f" Эту задачу взял {taken_by}. Только он может отметить выполнение!", show_alert=True)
            return

        mark_task_done(task_message_id)

        if repeat != 'none':
            new_message = await context.bot.send_message(
                chat_id=chat_id,
                text=f"**Задача возобновлена** (повтор: {repeat})",
                parse_mode='Markdown'
            )
            add_task(
                chat_id=chat_id,
                message_id=new_message.message_id,
                task_text=task_text,
                created_by=created_by,
                urgency=urgency,
                repeat=repeat
            )
            # Добавляем кнопки к новому сообщению
            keyboard = [
                [InlineKeyboardButton("Я сделаю!", callback_data="take_task")],
                [
                    InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{new_message.message_id}")
                ]
            ]
            await new_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))

        # Обновляем исходное сообщение
        urgency_icons = {"Не особо", "Важная", "Горит"}
        icon = urgency_icons.get(urgency)
        done_text = f"**ЗАДАЧА ВЫПОЛНЕНА!**\n\n" \
                    f"Задача от {created_by}:\n📋 {task_text}\n\n" \
                    f"Срочность была: {urgency}\n" \
                    f"Выполнил(а): {taken_by}\n" \
                    f"Выполнено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=task_message_id,
                text=done_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка при редактировании: {e}")

        await query.edit_message_text(
            text=f" Задача выполнена! Молодец, {user.full_name}!",
            parse_mode='Markdown'
        )

# ---------- Обработка текстовых сообщений (для редактирования) ----------
#async def handle_edit_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
 #   """Принимаем новый текст задачи от пользователя, который хочет отредактировать"""
  #  if 'editing_task' not in context.user_data:
   #     return
#    #task_message_id = context.user_data['editing_task']
 #   new_text = update.message.text
  #  task = get_task_by_message(task_message_id)
   # if not task:
    #    await update.message.reply_text("❌ Задача не найдена!")
     #   del context.user_data['editing_task']
      #  return
#
 #   # Обновляем текст в БД
  #  update_task_text(task_message_id, new_text)
#
    # Обновляем сообщение в чате
 #   try:
  #      chat_id = task[1]  # chat_id из кортежа
   #     await context.bot.edit_message_text(
    #        chat_id=chat_id,
     #       message_id=task_message_id,
      #      text=f"✏️ **Задача изменена:**\n{new_text}",
       #     parse_mode='Markdown'
        #)
    #except Exception as e:
     #   logger.error(f"Не удалось отредактировать сообщение: {e}")
#
 #   await update.message.reply_text("✅ Текст задачи обновлён!")
  #  del context.user_data['editing_task']
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
    print("СЕМЕЙНЫЙ БОТ ЗАПУЩЕН С НОВЫМИ ФУНКЦИЯМИ!")
    print("=" * 60)
    print("Редактирование, удаление, повтор, /my, напоминания")
    app.run_polling()
if __name__ == '__main__':
    while True:
        try:
            print("\n Запуск бота...")
            main()
            print(" Бот завершил работу")
            break
        except KeyboardInterrupt:
            print("\nБот остановлен")
            break
        except Exception as e:
            print(f"\n Ошибка: {e}")
            traceback.print_exc()
            print("\n Перезапуск через 10 секунд...")
            time.sleep(10)
