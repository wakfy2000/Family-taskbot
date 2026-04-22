import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import URGENCY_ICONS
from database import (
    get_task_by_message, take_task, mark_task_done, delete_task, add_task, update_task_urgency
)
from utils.keyboards import creator_task_keyboard, complete_task_keyboard, urgency_selection_keyboard

logger = logging.getLogger(__name__)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = query.data

    # Удаление задачи
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
        await query.edit_message_text("🗑 Задача удалена.", parse_mode='Markdown')
        return

    # Взять задачу
    if data == "take_task":
        message_id = query.message.message_id
        task = get_task_by_message(message_id)
        if not task:
            await query.edit_message_text("Задача не найдена!")
            return

        task_id, chat_id, msg_id, task_text, created_by, taken_by, created_at, status, urgency, repeat, taken_at = task
        if taken_by:
            await query.edit_message_text(
                text=query.message.text + f"\n\nЗадача уже взята: {taken_by}",
                parse_mode='Markdown'
            )
            return

        take_task(message_id, user.full_name)
        icon = URGENCY_ICONS.get(urgency, "⚪")
        repeat_str = f"🔁 Повтор: **{repeat}**\n" if repeat != 'none' else ""
        new_text = (
            f"{icon} **Задача от {created_by}:**\n"
            f"📋 {task_text}\n\n"
            f"⚡ Срочность: **{urgency}**\n"
            f"{repeat_str}"
            f"👤 **Взял(а): {user.full_name}**\n"
            f"🕒 Взято: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        await query.edit_message_text(text=new_text, parse_mode='Markdown')

        try:
            await context.bot.send_message(
                chat_id=user.id,
                text=f"Вы взяли задачу: {task_text}\nСрочность: {urgency}\nСоздатель: {created_by}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning("Не удалось отправить личное уведомление исполнителю")

        await query.message.reply_text(
            f"Отлично, {user.full_name}!\n{task_text}",
            parse_mode='Markdown',
            reply_markup=complete_task_keyboard(message_id)
        )
        return

    # Выполнение задачи
    if data.startswith('complete_'):
        task_message_id = int(data.split('_')[1])
        task = get_task_by_message(task_message_id)
        if not task:
            await query.answer("Задача не найдена!", show_alert=True)
            return

        task_id, chat_id, msg_id, task_text, created_by, taken_by, created_at, status, urgency, repeat, taken_at = task
        if taken_by != user.full_name:
            await query.answer(f"Эту задачу взял {taken_by}. Только он может отметить выполнение!", show_alert=True)
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
            await new_message.edit_reply_markup(reply_markup=creator_task_keyboard(new_message.message_id))

        done_text = (
            f"**ЗАДАЧА ВЫПОЛНЕНА!**\n\n"
            f"Задача от {created_by}:\n📋 {task_text}\n\n"
            f"Срочность была: {urgency}\n"
            f"Выполнил(а): {taken_by}\n"
            f"Выполнено: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
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
            text=f"Задача выполнена! Молодец, {user.full_name}!",
            parse_mode='Markdown'
        )
        return

    # Открыть меню выбора срочности
    if data.startswith('change_urgency_'):
        task_message_id = int(data.split('_')[2])
        task = get_task_by_message(task_message_id)
        if not task:
            await query.answer("Задача не найдена!", show_alert=True)
            return
        if task[4] != user.full_name:
            await query.answer("Только создатель может менять срочность!", show_alert=True)
            return

        await query.edit_message_reply_markup(
            reply_markup=urgency_selection_keyboard(task_message_id)
        )
        return

    # Выбрана конкретная срочность
    if data.startswith('urgency_'):
        parts = data.split('_')
        task_message_id = int(parts[1])
        new_urgency = '_'.join(parts[2:])  # на случай "Не особо"

        task = get_task_by_message(task_message_id)
        if not task:
            await query.answer("Задача не найдена!", show_alert=True)
            return
        if task[4] != user.full_name:
            await query.answer("Только создатель может менять срочность!", show_alert=True)
            return

        update_task_urgency(task_message_id, new_urgency)

        # Получаем обновлённые данные задачи
        task = get_task_by_message(task_message_id)
        task_id, chat_id, msg_id, task_text, created_by, taken_by, created_at, status, urgency, repeat, taken_at = task

        icon = URGENCY_ICONS.get(new_urgency, "⚪")
        repeat_str = f"🔁 Повтор: **{repeat}**\n" if repeat != 'none' else ""

        if taken_by:
            new_text = (
                f"{icon} **Задача от {created_by}:**\n"
                f"📋 {task_text}\n\n"
                f"⚡ Срочность: **{new_urgency}**\n"
                f"{repeat_str}"
                f"👤 **Взял(а): {taken_by}**\n"
                f"🕒 Взято: {taken_at[:16] if taken_at else ''}"
            )
        else:
            new_text = (
                f"{icon} **Новая задача от {created_by}:**\n"
                f"📋 {task_text}\n\n"
                f"⚡ Срочность: **{new_urgency}**\n"
                f"{repeat_str}"
                f"👤 Кто сделает?"
            )

        await query.edit_message_text(
            text=new_text,
            parse_mode='Markdown',
            reply_markup=creator_task_keyboard(task_message_id)
        )
        await query.answer(f"Срочность изменена на «{new_urgency}»")
        return

    # Кнопка "Назад" из меню срочности
    if data.startswith('back_to_task_'):
        task_message_id = int(data.split('_')[3])
        task = get_task_by_message(task_message_id)
        if not task:
            await query.answer("Задача не найдена!", show_alert=True)
            return
        await query.edit_message_reply_markup(
            reply_markup=creator_task_keyboard(task_message_id)
        )
        return