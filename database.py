"""Row-level operations for the password-protected shared workspace."""
import psycopg
from psycopg.rows import dict_row


def connect(url):
    return psycopg.connect(url, connect_timeout=8, row_factory=dict_row)


def ensure_schema(url):
    with connect(url) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(724039826)")
        conn.execute("""CREATE TABLE IF NOT EXISTS learning_tracker_tasks (
            id UUID PRIMARY KEY, title TEXT NOT NULL, category TEXT NOT NULL,
            completed BOOLEAN NOT NULL, deadline TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL)""")
        kind = conn.execute("""SELECT atttypid::regtype::text AS kind
            FROM pg_attribute WHERE attrelid='learning_tracker_tasks'::regclass
            AND attname='deadline' AND NOT attisdropped""").fetchone()["kind"]
        if kind == "date":
            conn.execute("""ALTER TABLE learning_tracker_tasks
                ALTER COLUMN deadline TYPE TIMESTAMPTZ
                USING ((deadline + TIME '23:59') AT TIME ZONE 'Asia/Almaty')""")
        elif kind != "timestamp with time zone":
            raise RuntimeError("Unsupported deadline column type.")

        conn.execute("""ALTER TABLE learning_tracker_tasks
            ADD COLUMN IF NOT EXISTS urgent BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS important BOOLEAN NOT NULL DEFAULT FALSE,
            ALTER COLUMN deadline DROP NOT NULL""")


def list_tasks(url):
    with connect(url) as conn:
        return conn.execute("SELECT * FROM learning_tracker_tasks ORDER BY created_at, id").fetchall()


def add(url, task):
    with connect(url) as conn:
        conn.execute("""INSERT INTO learning_tracker_tasks
            (id,title,category,completed,deadline,created_at,urgent,important) VALUES
            (%(id)s,%(title)s,%(category)s,%(completed)s,%(deadline)s,%(created_at)s,%(urgent)s,%(important)s)
            ON CONFLICT (id) DO NOTHING""", task)


def complete(url, ident, value):
    with connect(url) as conn:
        conn.execute("UPDATE learning_tracker_tasks SET completed=%s WHERE id=%s", (value, ident))


def delete(url, ident):
    with connect(url) as conn:
        conn.execute("DELETE FROM learning_tracker_tasks WHERE id=%s", (ident,))


def set_priority(url, ident, urgent, important):
    with connect(url) as conn:
        conn.execute("""UPDATE learning_tracker_tasks SET urgent=%s, important=%s
                        WHERE id=%s""", (urgent, important, ident))
