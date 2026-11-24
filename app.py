"""Learning Progress & Task Tracker. Run with streamlit run app.py."""
import hmac
import html
from datetime import date, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import plotly.graph_objects as go
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from deadlines import END_OF_DAY, ZONE, local_deadline, recognize, status
from tracker import CATEGORIES, MAX_TITLE_LENGTH, calculate_statistics, create_task, sample_tasks

from priority import FILTERS, GROUPS, QUADRANTS, SORTS, ordered, quadrant

S = st.session_state


def today():
    return datetime.now(ZONE).date()


def reset_draft():
    S.update(title="", quick="", day=today(), clock=END_OF_DAY, manual=False,
             draft_important=False, draft_urgent=False, clean="", issue="", detected=False, had_detection=False, draft_id=str(uuid4()))


def detect():
    S.clean, S.issue, S.detected = S.title.strip(), "", False
    if S.manual:
        return
    try:
        clean, inline = recognize(S.title, today())
        _, quick = recognize(S.quick, today(), standalone=True)
        if inline and quick and inline != quick:
            raise ValueError("The title and quick deadline disagree. Choose one deadline.")
        due = quick or inline
        S.clean = clean
        if due:
            S.day, S.clock, S.detected = due.date(), due.time(), True
        elif S.get("had_detection"):
            S.day, S.clock = today(), END_OF_DAY
    except ValueError as exc:
        S.issue = str(exc)
    S.had_detection = S.detected


def clear_deadline():
    if not S.issue:
        S.title = S.clean
    S.quick = ""
    S.day = None
    S.issue = ""
    S.detected = S.had_detection = False
    S.clean = S.title.strip()


def shortcut(days):
    S.day, S.clock = today() + timedelta(days=days), END_OF_DAY
    # Retain the cleaned title when overriding a recognized date.
    if S.issue:
        S.manual = True
        S.clean = S.title.strip()
    S.issue = ""
    S.detected = False


def chart(counts):
    done, left = counts["completed"], counts["remaining"]
    empty = done + left == 0
    figure = go.Figure(go.Pie(
        labels=["No tasks"] if empty else ["Completed", "Remaining"],
        values=[1] if empty else [done, left], hole=.79, sort=False,
        direction="clockwise", textinfo="none", showlegend=not empty,
        marker=dict(colors=["#2B3048"] if empty else ["#2546A0", "#A13D70"]),
        hoverinfo="skip" if empty else None,
        hovertemplate=None if empty else "%{label} · %{value} (%{percent})<extra></extra>"))
    figure.update_layout(
        height=250, margin=dict(l=4, r=4, t=5, b=5), template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#F1F3FA"), legend=dict(orientation="h", x=.5, xanchor="center",
        y=-.04, yanchor="top", itemclick=False, itemdoubleclick=False),
        annotations=[dict(x=.5, y=.5, text=f"<b>{counts['percentage']:.0f}%</b>",
                          showarrow=False, font=dict(size=35))])
    return figure


@st.cache_resource(show_spinner=False)
def prepare_database(_url, identity):
    import database
    database.ensure_schema(_url)
    return True


def mutate(mode, action, ident=None, value=None):
    demo = mode == "demo"
    if not demo:
        settings = st.secrets["postgres"]
        if not hmac.compare_digest(S.get("password", "").encode(), settings["workspace_password"].encode()):
            return
    if action == "add":
        if S.issue or not S.clean or (S.day and S.clock is None):
            S.notice = "Enter a task title and confirm its deadline."
            return
        due = datetime.combine(S.day, S.clock, ZONE) if S.day else None
        task = create_task(S.clean, S.category, due, urgent=S.draft_urgent, important=S.draft_important)
        task["id"] = S.draft_id
    try:
        if demo:
            if action == "add" and all(t["id"] != task["id"] for t in S.samples):
                S.samples.append(task)
            elif action == "delete":
                S.samples = [t for t in S.samples if t["id"] != ident]
            elif action in ("priority", "complete"):
                for t in S.samples:
                    if t["id"] == ident:
                        if action == "priority":
                            t["urgent"], t["important"] = value
                        else:
                            t["completed"] = value
        else:
            import database
            url = settings["url"]
            if action == "add":
                database.add(url, task)
            elif action == "priority":
                database.set_priority(url, ident, *value)
            elif action == "complete":
                database.complete(url, ident, value)
            else:
                database.delete(url, ident)
    except Exception:
        S.notice = "Could not confirm the change. Check the saved workspace and retry."
        return
    if action == "add":
        reset_draft()


def sidebar(mode):
    if "draft_id" not in S:
        reset_draft()
    st.subheader("Add a task")
    st.text_input("Task title", key="title", max_chars=MAX_TITLE_LENGTH,
                  placeholder="Study SQL tomorrow at 18:00", on_change=detect)
    st.selectbox("Category", CATEGORIES, key="category")
    important, urgent = st.columns(2)
    important.checkbox("Important", key="draft_important")
    urgent.checkbox("Urgent", key="draft_urgent")
    st.text_input("Quick deadline", key="quick", placeholder="Friday 15:30 · Завтра",
                  on_change=detect, disabled=S.manual)
    st.checkbox("Use literal title and manual deadline", key="manual", on_change=detect)
    for col, (label, days) in zip(st.columns(3), [("Today", 0), ("Tomorrow", 1), ("Next week", 7)]):
        col.button(label, key=f"quick-{days}", on_click=shortcut, args=(days,))
    a, b = st.columns([1.2, 1])
    a.date_input("Date", key="day", format="DD/MM/YYYY", min_value=min(date(1900, 1, 1), S.day or today()),
                 max_value=max(date(2100, 12, 31), S.day or today()))
    b.time_input("Time", key="clock", step=60)
    st.button("No deadline", key="clear-due", on_click=clear_deadline)
    if S.issue:
        st.warning(S.issue)
    else:
        if S.detected and S.clean != S.title.strip():
            st.text(S.clean)
        if S.day and S.clock is not None:
            st.caption(f"Deadline · {S.day:%d %b %Y} · {S.clock:%H:%M} Almaty")
    st.button("Add Task", type="primary", key="add", width="stretch",
              disabled=bool(S.issue), on_click=mutate, args=(mode, "add"))
    if notice := S.pop("notice", None):
        st.warning(notice)


def move_task(mode, ident, key):
    choice = S[key]
    mutate(mode, "priority", ident, QUADRANTS[choice][2:])


def priority_menu(task, mode, view):
    ident = task["id"]
    key = f"priority-{view}-{mode}-{ident}"
    S[key] = quadrant(task)
    st.selectbox("Move to quadrant", range(4), key=key,
                 format_func=lambda i: f"{QUADRANTS[i][0]} · {QUADRANTS[i][1]}",
                 on_change=move_task, args=(mode, ident, key))


def task_row(task, mode, view, now):
    ident = task["id"]
    due = local_deadline(task["deadline"]) if task.get("deadline") else None
    due_text = due.strftime("%d %b %Y · %H:%M") if due else "No deadline"
    done = task["completed"]
    state = status(due, done, now)
    badge_class = state.lower().replace(" ", "-")
    with st.container(border=view != "matrix", key=f"row-{view}-{mode}-{ident}"):
        if view in ("tasks", "matrix"):
            body, actions = st.columns([5, 1.4], vertical_alignment="center")
            with actions.popover("Edit" if view == "tasks" else "Move"):
                priority_menu(task, mode, view)
                if view == "tasks":
                    st.button("Delete", key=f"delete-{mode}-{ident}", on_click=mutate,
                              args=(mode, "delete", ident))
        else:
            body = st.container()
        with body:
            if view == "deadlines":
                st.text(task["title"])
            else:
                key = f"{view}-{mode}-{ident}-{int(done)}"
                # Render from the shared model, including after a failed database write.
                S[key] = done
                title = "".join(("\\" + c if c in r"\*_`[]~<>#$!" else c) for c in task["title"])
                st.checkbox(title, key=key, on_change=mutate,
                            args=(mode, "complete", ident, not done))
            st.markdown(f'<div class="task-meta"><span class="badge {badge_class}">{state}</span>'
                        f'<span>{html.escape(task["category"])}</span><time>{due_text}</time></div>',
                        unsafe_allow_html=True)


def main():
    import hashlib
    st.set_page_config(page_title="Learning Tracker", page_icon=":material/checklist:", layout="wide")
    st.markdown("<style>" + Path(__file__).with_name("style.css").read_text("utf-8") + "</style>",
                unsafe_allow_html=True)
    try:
        settings = st.secrets.get("postgres", {})
        source_url = st.secrets.get("repository_url", "")
    except StreamlitSecretNotFoundError:
        settings, source_url = {}, ""
    mode = "demo"
    if settings and st.sidebar.radio("Workspace", ["Sample demo", "Saved workspace"], key="workspace") == "Saved workspace":
        mode = "saved"
    st.title("Learning Tracker")
    if source_url.startswith("https://github.com/"):
        st.sidebar.link_button("Python source on GitHub", source_url)
    if mode == "demo":
        st.caption("Sample workspace · Changes last for this browser session.")
        if "samples" not in S:
            S.samples = sample_tasks(today())
        tasks = S.samples
    else:
        st.caption("Saved workspace · Shared tasks")
        if not settings.get("url") or not settings.get("workspace_password"):
            st.error("Configure both PostgreSQL settings to open this workspace.")
            return
        password = st.sidebar.text_input("Workspace password", type="password", key="password")
        if not hmac.compare_digest(password.encode(), settings["workspace_password"].encode()):
            st.caption("Enter the workspace password to open saved tasks.")
            return
        try:
            import database
            url = settings["url"]
            prepare_database(url, hashlib.sha256(url.encode()).hexdigest())
            tasks = database.list_tasks(url)
        except Exception:
            st.error("Saved workspace unavailable. Check the database connection and table permissions.")
            return
    with st.sidebar:
        sidebar(mode)
    overview, listing, deadlines, matrix = st.tabs(["Dashboard", "Tasks", "Deadlines", "Eisenhower Matrix"])
    now = datetime.now(ZONE)
    pending = ordered(tasks, SORTS[0], "Active", now)
    with overview:
        counts = calculate_statistics(tasks)
        a, b, c = st.columns(3)
        a.metric("Completed", counts["completed"])
        b.metric("Remaining", counts["remaining"])
        c.metric("Completion percentage", f"{counts['percentage']:.1f}%")
        st.progress(counts["percentage"] / 100)
        graph, active = st.columns([1, 1.4], gap="medium")
        with graph.container(border=True):
            st.subheader("Completion")
            st.plotly_chart(chart(counts), theme=None, width="stretch",
                            key="completion-chart", config={"displayModeBar": False})
        with active:
            st.subheader("Active Tasks")
            if not pending:
                st.caption("All tasks complete." if tasks else "Add your first task in the sidebar.")
            for task in pending:
                task_row(task, mode, "active", now)
    with listing:
        left, right = st.columns(2)
        sort = left.selectbox("Sort by", SORTS, key="task-sort")
        selection = right.selectbox("Filter", FILTERS, key="task-filter")
        visible = ordered(tasks, sort, selection, now)
        if not visible:
            st.caption("No matching tasks." if tasks else "Your task list is empty.")
        for task in visible:
            task_row(task, mode, "tasks", now)
    with deadlines:
        st.caption("Deadlines in Almaty time")
        scheduled = [t for t in pending if t.get("deadline")]
        if not scheduled:
            st.caption("No open deadlines.")
        for task in scheduled:
            task_row(task, mode, "deadlines", now)

    with matrix:
        render_matrix(tasks, mode, now)


def render_matrix(tasks, mode, now):
    grouped = [{} for _ in QUADRANTS]
    for task in ordered(tasks, SORTS[0], "All tasks", now):
        group = status(task.get("deadline"), task["completed"], now)
        name = "Later" if group == "Upcoming" else group
        grouped[quadrant(task)].setdefault(name, []).append(task)
    for start in (0, 2):
        cols = st.columns(2, gap="small")
        for index, col in enumerate(cols, start):
            number, title, _, _ = QUADRANTS[index]
            groups = grouped[index]
            active = sum(len(groups.get(g, [])) for g in GROUPS)
            with col.container(key=f"quadrant-{number}", height=350, border=True):
                st.html(f'<div class="quadrant-title tone-{number}" role="heading" aria-level="3">'
                        f'<small>{number}</small><strong>{title}</strong>'
                        f'<span>{active} active</span></div>')
                if not active:
                    st.caption("No active tasks")
                for group in GROUPS:
                    if group in groups:
                        st.caption(group)
                        for task in groups[group]:
                            task_row(task, mode, "matrix", now)
                completed = groups.get("Completed", [])
                with st.expander(f"Completed ({len(completed)})"):
                    for task in completed:
                        task_row(task, mode, "matrix", now)
                    if not completed:
                        st.caption("No completed tasks")


if __name__ == "__main__":
    main()
