"""Learning Progress & Task Tracker. Run with streamlit run app.py."""
import hmac
from datetime import date

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import psycopg
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

import database
from tracker import CATEGORIES, MAX_TITLE_LENGTH, calculate_statistics, create_task, sample_tasks


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


def main():
    st.set_page_config(page_title="Learning Tracker", page_icon="📚", layout="wide")
    st.title("Learning Progress & Task Tracker")
    try:
        settings = st.secrets.get("postgres", {})
        source_url = st.secrets.get("repository_url", "")
        if source_url.startswith("https://github.com/"):
            st.sidebar.link_button("Python source on GitHub", source_url)
    except StreamlitSecretNotFoundError:
        settings = {}
    demo = True
    if settings:
        mode = st.sidebar.radio("Workspace", ["Sample demo", "Saved workspace"])
        demo = mode == "Sample demo"

    if demo:
        st.info("Sample demo · Your edits last only for this browser session. Reload to start again.")
        if "samples" not in st.session_state:
            st.session_state.samples = sample_tasks(date.today())
        tasks = st.session_state.samples
    else:
        st.info("Saved workspace · Real tasks shared by everyone with the workspace password.")
        dsn = settings.get("url", "")
        password = settings.get("workspace_password", "")
        if not dsn or not password:
            st.error("The owner must configure both PostgreSQL settings in Streamlit secrets.")
            return
        entered = st.sidebar.text_input("Workspace password", type="password")
        if not hmac.compare_digest(entered.encode(), password.encode()):
            st.caption("Enter the workspace password to open saved tasks.")
            return
        tasks = database.list_tasks(dsn)

    with st.sidebar.form("add_sample" if demo else "add_saved", clear_on_submit=True):
        st.subheader("Add a task")
        title = st.text_input("Task title", max_chars=MAX_TITLE_LENGTH)
        category = st.selectbox("Category", CATEGORIES)
        due = st.date_input("Deadline", value=date.today())
        if st.form_submit_button("Add task"):
            if title.strip() and due:
                task = create_task(title, category, due)
                if demo:
                    tasks.append(task)
                else:
                    database.add(dsn, task)
                st.rerun()
            st.error("Enter a title and a deadline.")

    overview, listing, deadlines = st.tabs(["Dashboard", "Tasks", "Deadlines"])
    with overview:
        counts = calculate_statistics(tasks)
        cols = st.columns(4)
        for col, key in zip(cols, ["total", "completed", "remaining", "percentage"]):
            value = counts[key]
            col.metric("Completion" if key == "percentage" else key.title(),
                       f"{value:.1f}%" if key == "percentage" else value)
        st.progress(counts["percentage"] / 100)
        graph, categories = st.columns(2)
        with graph:
            figure = build_pie_chart(counts["completed"], counts["remaining"])
            st.pyplot(figure)
            plt.close(figure)
        with categories:
            st.subheader("Progress by category")
            for category in CATEGORIES:
                group = [t for t in tasks if t["category"] == category]
                done = sum(t["completed"] for t in group)
                st.write(f"{category} · {done} of {len(group)} completed")
    with listing:
        if not tasks:
            st.info("Add your first task in the sidebar.")
        for task in tasks:
            ident = task["id"]
            label, toggle, remove = st.columns([5, 2, 1])
            label.text(task["title"])
            label.caption(f"{task['category']} · Due {task['deadline']}")
            # Include the stored value in the key so external changes are reflected.
            checked = toggle.checkbox("Done", value=task["completed"],
                                      key=f"{demo}-{ident}-{task['completed']}")
            if checked != task["completed"]:
                if demo:
                    task["completed"] = checked
                else:
                    database.complete(dsn, ident, checked)
                st.rerun()
            if remove.button("Delete", key=f"delete-{demo}-{ident}"):
                if demo:
                    tasks.remove(task)
                else:
                    database.delete(dsn, ident)
                st.rerun()
    with deadlines:
        pending = sorted((t for t in tasks if not t["completed"]), key=lambda t: t["deadline"])
        if not pending:
            st.info("No open deadlines.")
        for task in pending:
            days = (task["deadline"] - date.today()).days
            when = "Overdue" if days < 0 else "Due today" if days == 0 else f"In {days} days"
            st.text(f"{task['deadline']} · {when} · {task['title']}")


if __name__ == "__main__":
    try:
        main()
    except psycopg.Error:
        st.error("Saved workspace unavailable. Check the database connection and permissions, then reload.")
