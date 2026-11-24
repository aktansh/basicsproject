import json
import unittest
from datetime import date, datetime, time, timedelta
from pathlib import Path

from streamlit.testing.v1 import AppTest

from deadlines import END_OF_DAY, ZONE, recognize, status

ROOT = Path(__file__).resolve().parents[1]


class DeadlineTest(unittest.TestCase):
    def test_languages(self):
        start = date(2026, 11, 24)
        for offset, hour, minute, words in [
            (0, 23, 59, ["Today", "Сегодня"]),
            (1, 23, 59, ["Wednesday", "Среда", "Tomorrow", "Завтра"]),
            (3, 15, 30, ["Friday 15:30", "Пятница 15:30"]),
            (6, 23, 59, ["Next Monday", "Следующий понедельник"]),
            (3, 23, 59, ["In 3 days", "Через 3 дня"]),
            (1, 14, 30, ["25/11/2026 14:30"]),
            (1, 18, 0, ["Tomorrow at 18:00", "Завтра в 18:00"]),
        ]:
            for word in words:
                with self.subTest(word=word):
                    title, due = recognize("Finish Python " + word, start)
                    self.assertEqual(title, "Finish Python")
                    self.assertEqual(due, datetime.combine(start + timedelta(days=offset),
                                                          time(hour, minute), ZONE))

    def test_ambiguous(self):
        for phrase in ["Friday or Monday", "today at 26:00", "31/11/2026", "03/04/2026",
                       "tomorrow morning", "after Friday", "in 3 hours"]:
            with self.subTest(phrase=phrase), self.assertRaises(ValueError):
                recognize(phrase, date(2026, 11, 24), standalone=True)

    def test_status(self):
        now = datetime(2026, 11, 24, 15, tzinfo=ZONE)
        for delta, label in [(-1, "Overdue"), (1, "Today"), (1440, "Tomorrow"), (3000, "Upcoming")]:
            self.assertEqual(status(now + timedelta(minutes=delta), False, now), label)
        self.assertEqual(status(now, True, now), "Completed")


class DemoTest(unittest.TestCase):
    def setUp(self):
        self.at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
        self.assertFalse(self.at.exception)

    def counts(self, done, left):
        at = self.at
        self.assertFalse(at.exception)
        percent = 100 * done / (done + left) if done + left else 0
        self.assertEqual([m.value for m in at.metric], [str(done), str(left), f"{percent:.1f}%"])
        spec = json.loads(at.get("plotly_chart")[0].proto.spec)
        self.assertEqual(spec["data"][0]["values"], [done, left] if done + left else [1])
        self.assertEqual(at.get("progress")[0].proto.value, int(percent))

    def test_professor_walkthrough(self):
        at = self.at
        self.counts(2, 2)
        at.text_input(key="title").set_value("Professor test завтра в 18:00").run()
        self.assertEqual(at.time_input(key="clock").value, time(18))
        self.assertEqual(at.date_input(key="day").value, datetime.now(ZONE).date() + timedelta(days=1))
        at.time_input(key="clock").set_value(time(14, 17)).run()
        at.date_input(key="day").set_value(date(2020, 1, 2)).run()
        at.button(key="add").click().run()
        self.counts(2, 3)
        task = at.session_state.samples[-1]
        self.assertEqual(task["title"], "Professor test")
        self.assertEqual(task["deadline"], datetime(2020, 1, 2, 14, 17, tzinfo=ZONE))
        active = [c for c in at.checkbox if c.key.startswith("active-")]
        self.assertEqual(active[0].label, "Professor test")
        self.assertTrue(any('badge overdue' in m.value for m in at.markdown))
        active[0].check().run()
        self.counts(3, 2)
        self.assertFalse(any(c.label == "Professor test" and c.key.startswith("active-") for c in at.checkbox))
        next(c for c in at.checkbox if c.label == "Professor test").uncheck().run()
        self.counts(2, 3)
        at.button(key=f"delete-demo-{task['id']}").click().run()
        self.counts(2, 2)

    def test_quick_entry_and_empty(self):
        at = self.at
        for task in list(at.session_state.samples):
            at.button(key=f"delete-demo-{task['id']}").click().run()
        self.counts(0, 0)
        at.text_input(key="title").set_value("Assignment").run()
        at.text_input(key="quick").set_value("Friday or Wednesday").run()
        self.assertTrue(at.button(key="add").disabled)
        at.text_input(key="quick").set_value("In 3 days").run()
        self.assertEqual(at.time_input(key="clock").value, END_OF_DAY)
        at.button(key="quick-7").click().run()
        target = datetime.now(ZONE).date() + timedelta(days=7)
        self.assertEqual(at.date_input(key="day").value, target)
        at.button(key="add").click().run()
        self.counts(0, 1)
        at.button(key="add").click().run()
        self.counts(0, 1)
