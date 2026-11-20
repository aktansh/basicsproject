"""
Learning Progress & Task Tracker
A small Streamlit app that stores tasks in a local JSON file.
Run with: streamlit run app.py
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import streamlit as st


# Keep the JSON file beside app.py so it remains available after page reloads.
APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "tasks.json"

CATEGORIES = ("Studies", "Project", "Personal")
MAX_TITLE_LENGTH = 120

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)


def load_tasks(path: Path = DATA_FILE) -> tuple[list[dict[str, Any]], list[str], str | None]:
    """
    Load and validate tasks from JSON.

    Returns:
        (tasks, warnings, error)
        If the JSON file is unreadable or has an invalid top-level structure,
        error is returned and the app will disable editing rather than
        accidentally overwriting the user's data.
    """
    if not path.exists():
        return [], [], None

    try:
        with path.open("r", encoding="utf-8") as json_file:
            payload = json.load(json_file)
    except json.JSONDecodeError as exc:
        message = (
            f"{path.name} contains invalid JSON "
            f"(line {exc.lineno}, column {exc.colno})."
        )
        LOGGER.exception("Could not parse task data")
        return [], [], message
    except OSError as exc:
        LOGGER.exception("Could not read task data")
        return [], [], f"Could not read {path.name}: {exc}"

    # Accept both the current {"version": 1, "tasks": [...]} format
    # and a plain list for easier recovery from older/simple versions.
    if isinstance(payload, list):
        raw_tasks = payload
    elif isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
        raw_tasks = payload["tasks"]
    else:
        return [], [], (
            f"{path.name} has an unexpected structure. "
            "Expected a JSON object containing a 'tasks' list."
        )

    tasks: list[dict[str, Any]] = []
    warnings: list[str] = []
    used_ids: set[str] = set()

    for position, item in enumerate(raw_tasks, start=1):
        if not isinstance(item, dict):
            warnings.append(f"Skipped task #{position}: it is not a JSON object.")
            continue

        title = item.get("title")
        if not isinstance(title, str) or not title.strip():
            warnings.append(f"Skipped task #{position}: its title is missing.")
            continue

        title = title.strip()[:MAX_TITLE_LENGTH]

        category = item.get("category")
        if category not in CATEGORIES:
            category = "Personal"
            warnings.append(
                f"Task '{title}' had an unknown category; it was set to Personal."
            )

        task_id = str(item.get("id") or uuid.uuid4())
        if task_id in used_ids:
            task_id = str(uuid.uuid4())
            warnings.append(f"Task '{title}' had a duplicate ID; a new ID was assigned.")
        used_ids.add(task_id)

        completed = item.get("completed", False)
        if not isinstance(completed, bool):
            completed = False
            warnings.append(
                f"Task '{title}' had an invalid completion value; it was set to incomplete."
            )

        created_at = item.get("created_at")
        if not isinstance(created_at, str):
            created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

        tasks.append(
            {
                "id": task_id,
                "title": title,
                "category": category,
                "completed": completed,
                "created_at": created_at,
            }
        )

    return tasks, warnings, None


def save_tasks(tasks: list[dict[str, Any]], path: Path = DATA_FILE) -> None:
    """
    Save tasks safely with an atomic replace.

    Writing to a temporary file first helps prevent a partially written
    tasks.json file if the app is interrupted during saving.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "tasks": tasks}
    temporary_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f"{path.stem}_",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = temporary_file.name
            json.dump(payload, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())

        os.replace(temporary_path, path)
    except OSError:
        LOGGER.exception("Could not save task data")
        if temporary_path and os.path.exists(temporary_path):
            try:
                os.remove(temporary_path)
            except OSError:
                LOGGER.exception("Could not remove temporary task file")
        raise


def create_task(title: str, category: str) -> dict[str, Any]:
    """Create a new task with a unique ID and UTC creation timestamp."""
    return {
        "id": str(uuid.uuid4()),
        "title": title.strip()[:MAX_TITLE_LENGTH],
        "category": category,
        "completed": False,
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


def build_pie_chart(completed: int, remaining: int):
    """Build a pie chart, or a clear no-data placeholder when there are no tasks."""
    figure, axis = plt.subplots(figsize=(5, 4))

    if completed + remaining == 0:
        axis.text(
            0.5,
            0.5,
            "No tasks yet",
            horizontalalignment="center",
            verticalalignment="center",
            fontsize=14,
        )
        axis.axis("off")
    else:
        axis.pie(
            [completed, remaining],
            labels=["Completed", "Not completed"],
            autopct="%1.1f%%",
            startangle=90,
            wedgeprops={"edgecolor": "white", "linewidth": 1},
        )
        axis.set_title("Task completion")
        axis.axis("equal")

    figure.tight_layout()
    return figure


def render_task_list(
    tasks: list[dict[str, Any]],
    storage_available: bool,
) -> tuple[bool, str | None]:
    """
    Render task checkboxes and delete buttons.

    Returns whether any task changed and the ID of a task selected for deletion.
    Changes are saved by the caller in one JSON write.
    """
    has_changes = False
    task_to_delete: str | None = None

    for task in tasks:
        checkbox_key = f"task_completed_{task['id']}"

        # Seed checkbox state once. Streamlit then retains its value on reruns.
        if checkbox_key not in st.session_state:
            st.session_state[checkbox_key] = task["completed"]

        checkbox_col, details_col, delete_col = st.columns([0.12, 0.68, 0.20])

        with checkbox_col:
            st.checkbox(
                "Done",
                key=checkbox_key,
                disabled=not storage_available,
            )

        # Compare the widget state with the value loaded from JSON.
        if st.session_state[checkbox_key] != task["completed"]:
            task["completed"] = st.session_state[checkbox_key]
            has_changes = True

        with details_col:
            st.write(task["title"])
            state_label = "Completed" if task["completed"] else "In progress"
            st.caption(f"{task['category']} · {state_label}")

        with delete_col:
            if st.button(
                "Delete",
                key=f"delete_{task['id']}",
                disabled=not storage_available,
                use_container_width=True,
            ):
                task_to_delete = task["id"]

        st.divider()

    return has_changes, task_to_delete


def main() -> None:
    """Run the Streamlit user interface."""
    st.set_page_config(
        page_title="Learning Progress Tracker",
        page_icon="📚",
        layout="wide",
    )

    st.title("📚 Learning Progress & Task Tracker")
    st.caption("Organize your studies, projects, and personal tasks.")

    tasks, load_warnings, load_error = load_tasks()
    storage_available = load_error is None

    for warning in load_warnings:
        st.warning(warning)

    if load_error:
        st.error(
            f"Task storage could not be loaded: {load_error} "
            "Editing is disabled to protect the existing JSON data."
        )
        st.info(
            f"Check the file at: {DATA_FILE}. Correct its JSON format, "
            "then refresh the app."
        )

    # Sidebar form for adding tasks.
    with st.sidebar:
        st.header("Add a task")
        with st.form("add_task_form", clear_on_submit=True):
            task_title = st.text_input(
                "Task Title",
                max_chars=MAX_TITLE_LENGTH,
                placeholder="For example: Finish SQL homework",
            )
            task_category = st.selectbox("Category", CATEGORIES)
            submitted = st.form_submit_button(
                "Add task",
                use_container_width=True,
                disabled=not storage_available,
            )

        if submitted:
            cleaned_title = task_title.strip()
            if not cleaned_title:
                st.error("Enter a task title before adding the task.")
            else:
                tasks.append(create_task(cleaned_title, task_category))
                try:
                    save_tasks(tasks)
                except OSError as exc:
                    st.error(f"Could not save the task: {exc}")
                else:
                    st.rerun()

        st.divider()
        st.caption(f"Data is stored locally in `{DATA_FILE.name}`.")

    # Statistics.
    statistics = calculate_statistics(tasks)
    total = int(statistics["total"])
    completed = int(statistics["completed"])
    remaining = int(statistics["remaining"])
    percentage = float(statistics["percentage"])

    st.subheader("Your progress")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Completion", f"{percentage:.1f}%")
    metric_columns[1].metric("Total tasks", total)
    metric_columns[2].metric("Completed", completed)
    metric_columns[3].metric("Remaining", remaining)

    st.progress(
        percentage / 100,
        text=f"{percentage:.1f}% of tasks completed",
    )

    chart_column, overview_column = st.columns([1, 1])

    with chart_column:
        st.subheader("Completion breakdown")
        chart = build_pie_chart(completed, remaining)
        st.pyplot(chart, use_container_width=True)
        plt.close(chart)

    with overview_column:
        st.subheader("Task overview")
        if total == 0:
            st.info("No tasks yet. Add your first task from the sidebar.")
        else:
            st.write(f"**{completed}** completed out of **{total}** tasks.")
            st.write(f"**{remaining}** task(s) still need attention.")
            category_counts = {
                category: sum(1 for task in tasks if task["category"] == category)
                for category in CATEGORIES
            }
            for category, count in category_counts.items():
                st.write(f"{category}: {count}")

    # Main task list.
    st.subheader("Tasks")
    if not tasks:
        st.info("Your task list is empty.")
    else:
        has_changes, task_to_delete = render_task_list(tasks, storage_available)

        # Persist all checkbox changes and deletions in a single write.
        if task_to_delete is not None:
            tasks = [task for task in tasks if task["id"] != task_to_delete]
            has_changes = True

        if has_changes and storage_available:
            try:
                save_tasks(tasks)
            except OSError as exc:
                st.error(f"Could not save your changes: {exc}")
            else:
                st.rerun()


if __name__ == "__main__":
    main()
