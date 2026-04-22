from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def take_task_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Я сделаю!", callback_data="take_task")]
    ])


def creator_task_keyboard(message_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Я сделаю!", callback_data="take_task")],
        [
            InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{message_id}"),
            InlineKeyboardButton("⚡ Срочность", callback_data=f"change_urgency_{message_id}")
        ]
    ])


def complete_task_keyboard(message_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Задача выполнена", callback_data=f"complete_{message_id}")]
    ])


def urgency_selection_keyboard(message_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 Не особо", callback_data=f"urgency_{message_id}_Не особо")],
        [InlineKeyboardButton("🔵 Важная", callback_data=f"urgency_{message_id}_Важная")],
        [InlineKeyboardButton("🔴 Горит", callback_data=f"urgency_{message_id}_Горит")],
        [InlineKeyboardButton("« Назад", callback_data=f"back_to_task_{message_id}")]
    ])