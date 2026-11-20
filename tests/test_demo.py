import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class DemoTest(unittest.TestCase):
    def test_professor_walkthrough(self):
        app = Path(__file__).resolve().parents[1] / "app.py"
        at = AppTest.from_file(str(app), default_timeout=30).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[3].value, "50.0%")
        at.text_input[0].set_value("Professor test")
        at.sidebar.button[0].click().run()
        self.assertEqual(at.metric[3].value, "40.0%")
        at.checkbox[-1].check().run()
        self.assertEqual(at.metric[3].value, "60.0%")
        at.checkbox[-1].uncheck().run()
        next(b for b in reversed(list(at.button)) if b.label == "Delete").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.metric[3].value, "50.0%")
