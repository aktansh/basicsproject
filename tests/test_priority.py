import unittest
from datetime import datetime, timedelta

from deadlines import ZONE
from priority import SORTS, ordered, quadrant
from tracker import create_task
from test_demo import ROOT
from streamlit.testing.v1 import AppTest


class PriorityTest(unittest.TestCase):
    def test_sort_orders_and_old_records(self):
        now = datetime(2026, 11, 24, 14, tzinfo=ZONE)
        titles = ["zebra", "Әлем", "Ёж", "английский", "Alpha"]
        rows = [create_task(t, "Studies", now + timedelta(hours=i-2)) for i,t in enumerate(titles)]
        for i,t in enumerate(rows):
            t["created_at"] = now + timedelta(minutes=i)
        rows[0]["deadline"] = None
        rows[1]["urgent"] = rows[1]["important"] = True
        rows[3]["completed"] = True
        rows[0].pop("important")
        rows[0].pop("urgent")
        self.assertEqual(quadrant(rows[0]), 3)
        for sort, indices in zip(SORTS[:6], [
            [1,2,3,4,0], [4,3,2,1,0], [4,0,3,1,2], [2,1,3,0,4], [4,3,2,1,0], [0,1,2,3,4]
        ]):
            with self.subTest(sort=sort):
                self.assertEqual(ordered(rows, sort, "All tasks", now), [rows[i] for i in indices])
        self.assertEqual(ordered(rows, SORTS[6], "Active", now)[0], rows[1])
        self.assertEqual(ordered(rows, SORTS[7], "All tasks", now)[-1], rows[3])
        self.assertEqual(ordered(rows, SORTS[3], "Overdue", now), [rows[1]])
        self.assertEqual(ordered(rows, SORTS[1], "Completed", now), [rows[3]])

    def test_matrix_workflow(self):
        at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertEqual([t.label for t in at.tabs], ["Dashboard", "Tasks", "Deadlines", "Eisenhower Matrix"])
        for index, flags in enumerate([(True, True), (False, True), (True, False), (False, False)]):
            at.text_input(key="title").set_value(f"Priority {index}").run()
            at.checkbox(key="draft_urgent").set_value(flags[0]).run()
            at.checkbox(key="draft_important").set_value(flags[1]).run()
            at.button(key="clear-due").click().run()
            at.button(key="add").click().run()
            task = at.session_state.samples[-1]
            self.assertEqual(quadrant(task), index)
            self.assertIsNone(task["deadline"])
        ident = task["id"]
        at.selectbox(key=f"priority-matrix-demo-{ident}").set_value(1).run()
        self.assertEqual(quadrant(at.session_state.samples[-1]), 1)
        at.selectbox(key=f"priority-tasks-demo-{ident}").set_value(0).run()
        self.assertEqual(quadrant(at.session_state.samples[-1]), 0)
        at.checkbox(key=f"matrix-demo-{ident}-0").check().run()
        self.assertEqual(at.metric[0].value, "3")
        self.assertTrue(at.checkbox(key=f"tasks-demo-{ident}-1").value)
        self.assertFalse(any(c.key == f"active-demo-{ident}-0" for c in at.checkbox))
        at.selectbox(key="task-sort").set_value(SORTS[3]).run()
        at.selectbox(key="task-filter").set_value("Completed").run()
        at.checkbox(key=f"matrix-demo-{ident}-1").uncheck().run()
        self.assertEqual(at.metric[0].value, "2")
        self.assertFalse(any(c.key == f"tasks-demo-{ident}-0" for c in at.checkbox))
        self.assertTrue(any(c.key == f"active-demo-{ident}-0" for c in at.checkbox))
        self.assertEqual(at.selectbox(key="task-sort").value, SORTS[3])
        self.assertFalse(at.exception)
