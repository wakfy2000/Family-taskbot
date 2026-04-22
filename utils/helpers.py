import re

REPEAT_PATTERNS = {
    r'\bкаждый день\b': 'daily',
    r'\bкаждую неделю\b': 'weekly',
    r'\bкаждый месяц\b': 'monthly'
}


def parse_task_text(raw_text):
    urgency = "Важная"
    repeat = "none"
    task_parts = raw_text.strip()

    if task_parts.lower().endswith(" горит"):
        urgency = "Горит"
        task_text = task_parts[:-6].strip()
    elif task_parts.lower().endswith(" не особо"):
        urgency = "Не особо"
        task_text = task_parts[:-9].strip()
    else:
        task_text = task_parts

    for pattern, rep in REPEAT_PATTERNS.items():
        if re.search(pattern, task_text, re.IGNORECASE):
            repeat = rep
            task_text = re.sub(pattern, '', task_text, flags=re.IGNORECASE).strip()
            break

    return task_text, urgency, repeat