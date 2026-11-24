"""Manual priority, deadline grouping and task-list ordering."""
from datetime import datetime, timezone
from unicodedata import normalize

from deadlines import local_deadline, status

QUADRANTS = (
    ("I", "Urgent & Important", True, True),
    ("II", "Not Urgent & Important", False, True),
    ("III", "Urgent & Unimportant", True, False),
    ("IV", "Not Urgent & Unimportant", False, False),
)
SORTS = ("Deadline: earliest first", "Deadline: latest first", "Alphabetical: A–Z",
         "Alphabetical: Z–A", "Date created: newest first", "Date created: oldest first",
         "Priority: highest first", "Completion status")
FILTERS = ("All tasks", "Active", "Completed", "Overdue")
GROUPS = ("Overdue", "Today", "Tomorrow", "Later", "No Date")
# Kazakh Cyrillic also preserves the Russian alphabet's relative order.
ALPHABET = {c: i for i, c in enumerate("abcdefghijklmnopqrstuvwxyzаәбвгғдеёжзийкқлмнңоөпрстуұүфхһцчшщъыіьэюя")}


def quadrant(task):
    return (0 if task.get("important") else 2) + (0 if task.get("urgent") else 1)


def title_key(task):
    text = normalize("NFC", task["title"].strip().casefold())
    return tuple(ALPHABET.get(c, 100 + ord(c)) for c in text)


def created_key(task):
    value = task.get("created_at")
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value or datetime.min.replace(tzinfo=timezone.utc)


def ordered(tasks, sort, selection, now):
    def matches(task):
        if selection == "Overdue":
            return status(task.get("deadline"), task["completed"], now) == "Overdue"
        return selection == "All tasks" or task["completed"] == (selection == "Completed")

    rows = sorted((t for t in tasks if matches(t)), key=lambda t: str(t["id"]))
    if sort in SORTS[:2]:
        dated = [t for t in rows if t.get("deadline")]
        dated.sort(key=lambda t: local_deadline(t["deadline"]), reverse=sort == SORTS[1])
        return dated + [t for t in rows if not t.get("deadline")]
    keys = (title_key, title_key, created_key, created_key, quadrant, lambda t: t["completed"])
    return sorted(rows, key=keys[SORTS.index(sort) - 2], reverse=sort in (SORTS[3], SORTS[4]))
