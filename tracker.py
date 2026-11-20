from datetime import date, datetime, timedelta, timezone
from typing import Any
import uuid

CATEGORIES = ("Studies", "Project", "Personal")
MAX_TITLE_LENGTH = 120


def create_task(title: str, category: str, deadline: date) -> dict[str, Any]:
    """Create a new task with a unique ID and UTC creation timestamp."""
    return {
        "id": str(uuid.uuid4()),
        "title": title.strip()[:MAX_TITLE_LENGTH],
        "category": category,
        "completed": False,
        "deadline": deadline,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
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
    for title, category, days, completed in examples:
        task = create_task(title, category, today + timedelta(days=days))
        task["completed"] = completed
        tasks.append(task)
    return tasks
