"""Row-level operations for the password-protected shared workspace."""
import psycopg
from psycopg.rows import dict_row


def connect(url):
    return psycopg.connect(url, connect_timeout=8, row_factory=dict_row)


def list_tasks(url):
    with connect(url) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS learning_tracker_tasks (
            id UUID PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
            completed BOOLEAN NOT NULL, deadline DATE NOT NULL,
            created_at TIMESTAMPTZ NOT NULL)""")
        return conn.execute("SELECT * FROM learning_tracker_tasks ORDER BY created_at, id").fetchall()


def add(url, task):
    with connect(url) as conn:
        conn.execute("""INSERT INTO learning_tracker_tasks
            (id,title,category,completed,deadline,created_at) VALUES
            (%(id)s,%(title)s,%(category)s,%(completed)s,%(deadline)s,%(created_at)s)
            ON CONFLICT (id) DO NOTHING""", task)


def complete(url, ident, value):
    with connect(url) as conn:
        conn.execute("UPDATE learning_tracker_tasks SET completed=%s WHERE id=%s", (value, ident))


def delete(url, ident):
    with connect(url) as conn:
        conn.execute("DELETE FROM learning_tracker_tasks WHERE id=%s", (ident,))
