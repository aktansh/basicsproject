"""Calendar deadlines for the Learning Tracker workspace."""
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Asia/Almaty")
END_OF_DAY = time(23, 59)
WEEKDAYS = [
    ("monday", "понедельник"), ("tuesday", "вторник"),
    ("wednesday", "среда", "среду"), ("thursday", "четверг"),
    ("friday", "пятница", "пятницу"), ("saturday", "суббота", "субботу"),
    ("sunday", "воскресенье"),
]
DAY_INDEX = {word: i for i, words in enumerate(WEEKDAYS) for word in words}
WEEKDAY = "|".join(DAY_INDEX)
RELATIVE = r"today|tomorrow|сегодня|завтра"
OFFSET = r"in\s+\d+\s+days?|через\s+\d+\s+(?:день|дня|дней)"
NUMERIC = r"\d{1,2}/\d{1,2}/\d{4}"
NEXT = r"next|следующий|следующая|следующую|следующее"
DATE_TOKEN = rf"(?:{RELATIVE}|{OFFSET}|{NUMERIC}|(?:(?:{NEXT})\s+)?(?:{WEEKDAY}))"
TOKEN = re.compile(rf"(?<!\w){DATE_TOKEN}(?!\w)", re.I)
CLOCK = re.compile(r"(?:\s+(?:(?:at|в)\s+)?(\d{1,2}):(\d{2}))?", re.I)
SUSPICIOUS = re.compile(r"\b(?:yesterday|tonight|weekend|noon|midnight|послезавтра|вечером|утром|через|next|следующ\w*|in\s+\d+)\b|\b\d+[./-]\d+|\b\d{1,2}:\d{2}", re.I)
MANUAL = "Choose a single deadline, or select manual entry to use the pickers."


def local_deadline(value):
    if isinstance(value, datetime):
        return value.astimezone(ZONE) if value.tzinfo else value.replace(tzinfo=ZONE)
    return datetime.combine(value, END_OF_DAY, ZONE)


def status(deadline, completed, now):
    if completed:
        return "Completed"
    due = local_deadline(deadline)
    now = now.astimezone(ZONE)
    if due < now:
        return "Overdue"
    days = (due.date() - now.date()).days
    return {0: "Today", 1: "Tomorrow"}.get(days, "Upcoming")


def recognize(text, today, *, standalone=False):
    """Return (clean title, deadline). Reject partial or conflicting expressions."""
    text = text.strip()
    matches = list(TOKEN.finditer(text))
    if not matches and not (standalone and text) and not SUSPICIOUS.search(text):
        return text, None
    if len(matches) != 1:
        raise ValueError(MANUAL)
    found = matches[0]
    prefix = text[:found.start()].strip()
    clock = CLOCK.fullmatch(text[found.end():])
    if (standalone and prefix) or clock is None or SUSPICIOUS.search(prefix):
        raise ValueError(MANUAL)
    # Qualifiers change calendar meaning. Never strip just the weekday.
    if re.search(r"\b(?:last|every|after|before|or|until|через|после|до|или|прошл\w*|кажд\w*)$", prefix, re.I):
        raise ValueError(MANUAL)
    token = found.group().casefold()
    try:
        hour, minute = clock.groups()
        due_time = time(int(hour), int(minute)) if hour else END_OF_DAY
        if "/" in token:
            day, month, year = map(int, token.split("/"))
            if day <= 12 and month <= 12 and day != month:
                raise ValueError
            due_date = date(year, month, day)
        elif token in ("today", "сегодня", "tomorrow", "завтра"):
            due_date = today + timedelta(days=int(token in ("tomorrow", "завтра")))
        elif token.startswith(("in ", "через")):
            due_date = today + timedelta(days=int(re.search(r"\d+", token).group()))
        else:
            words = token.split()
            index = DAY_INDEX[words[-1]]
            offset = (index - today.weekday()) % 7 or 7
            if len(words) == 2:
                offset = 7 - today.weekday() + index
            due_date = today + timedelta(days=offset)
        return prefix, datetime.combine(due_date, due_time, ZONE)
    except (ValueError, OverflowError, KeyError):
        raise ValueError(MANUAL) from None
