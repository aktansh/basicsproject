from datetime import date, datetime, timedelta, timezone
from typing import Any
import uuid

from deadlines import local_deadline

CATEGORIES = ("Studies", "Project", "Personal")
MAX_TITLE_LENGTH = 120


def create_task(title: str, category: str, deadline: date | None, *,
                urgent: bool = False, important: bool = False) -> dict[str, Any]:
    """Create a new task with a unique ID and UTC creation timestamp."""
    return {
        "id": str(uuid.uuid4()),
        "title": title.strip()[:MAX_TITLE_LENGTH],
        "category": category,
        "completed": False,
        "deadline": local_deadline(deadline) if deadline is not None else None,
        "urgent": urgent,
        "important": important,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def calculate_statistics(tasks: list[dict[str, Any]]) -> dict[str, int | float]:
    """Calculate task totals and completion percentage, including the empty case."""
    total = len(tasks)
    completed = sum(1 for task in tasks if task["completed"])
    remaining = total - completed
    percentage = (completed / total * 100) if total else 0.0

    return {
        "total": total,
        "completed": completed,
        "remaining": remaining,
        "percentage": percentage,
    }


def sample_tasks(today: date) -> list[dict]:
    examples = [
        ("Review SQL joins", "Studies", -1, True),
        ("Practice English past tense", "Studies", 0, False),
        ("Prepare project presentation", "Project", 3, False),
        ("Read one chapter", "Personal", 5, True),
    ]
    tasks = []
    for index, (title, category, days, completed) in enumerate(examples):
        task = create_task(title, category, today + timedelta(days=days),
                           urgent=index in (0, 1), important=index in (1, 2))
        task["completed"] = completed
        tasks.append(task)
    return tasks
