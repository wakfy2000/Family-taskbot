import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import URGENCY_ICONS
from database import add_task, get_chat_tasks, get_user_tasks
from utils.helpers import parse_task_text
from utils.keyboards import creator_task_keyboard, take_task_keyboard

logger = logging.getLogger(__name__)


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

    raw_text = " ".join(context.args)
    task_text, urgency, repeat = parse_task_text(raw_text)
    user = update.effective_user
    icon = URGENCY_ICONS.get(urgency, "⚪")

    message = await update.effective_chat.send_message(
        f"{icon} **Новая задача от {user.full_name}:**\n"
        f"📋 {task_text}\n\n"
        f"⚡ Срочность: **{urgency}**\n"
        f"🔁 Повтор: **{repeat if repeat != 'none' else 'нет'}**\n"
        f"👤 Кто сделает?",
        parse_mode='Markdown',
        reply_markup=take_task_keyboard()
    )

    add_task(
        chat_id=update.effective_chat.id,
        message_id=message.message_id,
        task_text=task_text,
        created_by=user.full_name,
        urgency=urgency,
        repeat=repeat
    )

    await message.edit_reply_markup(reply_markup=creator_task_keyboard(message.message_id))

    try:
        await context.bot.send_message(
            chat_id=user.id,
            text=f"Вы создали задачу: {task_text}\n"
                 f"Срочность: {urgency}\n"
                 f"Повтор: {repeat}\n"
                 f"Ожидайте исполнителя.",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.warning("Не удалось отправить личное уведомление создателю")

    try:
        await update.message.delete()
    except Exception:
        pass


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Эта команда работает только в группах!")
        return

    tasks = get_chat_tasks(update.effective_chat.id)
    if not tasks:
        await update.message.reply_text("Пока нет задач!")
        return

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
            icon = URGENCY_ICONS.get(urgency, "⚪")
            repeat_str = f" {repeat}" if repeat != 'none' else ''
            message_text += f"{icon} {task_text}\n  👤Создал: {created_by} | {urgency}{repeat_str}\n\n"
    if taken_tasks:
        message_text += " **В работе:**\n"
        for task_text, created_by, taken_by, urgency, repeat in taken_tasks:
            icon = URGENCY_ICONS.get(urgency, "⚪")
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
            icon = URGENCY_ICONS.get(urgency, "⚪")
            repeat_str = f"{repeat}" if repeat != 'none' else ''
            message_text += f"{icon} {task_text}\n  от {created_by} | {urgency}{repeat_str}\n\n"
    if done_tasks:
        message_text += "**Выполнено:**\n"
        for task_text, created_by, urgency, repeat in done_tasks:
            message_text += f" {task_text}\n от {created_by}\n\n"

    await update.message.reply_text(message_text, parse_mode='Markdown')