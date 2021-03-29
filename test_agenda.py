#!/usr/bin/env python

import datetime
from io import StringIO
import unittest

import agenda


class TestAgenda(unittest.TestCase):
    def test_load_conf(self):
        self.assertEqual(
            agenda.load_conf(StringIO(CONF)),
            {
                'messages': {
                    0: {'offset': 3, 'text': '# %Y-%m-%d Planning'},
                    3: {'offset': 1, 'text': '# %Y-%m-%d Grooming'},
                },
                'period': 21,
                'start': datetime.datetime(2020, 2, 21, 0, 0),
            },
        )

    def test_compute_message(self):
        conf = agenda.load_conf(StringIO(CONF))
        now = datetime.datetime(2020, 2, 21, 17, 0)
        self.assertEqual(agenda.compute_message(now, conf), '# 2020-02-24 Planning')
        now = datetime.datetime(2020, 2, 22, 17, 0)
        self.assertEqual(agenda.compute_message(now, conf), None)
        now = datetime.datetime(2020, 2, 23, 17, 0)
        self.assertEqual(agenda.compute_message(now, conf), None)
        now = datetime.datetime(2020, 2, 24, 17, 0)
        self.assertEqual(agenda.compute_message(now, conf), '# 2020-02-25 Grooming')


CONF = '''
---
period: 21
start: 2020-02-21
messages:
  # Friday week0
  0:
    text: "# %Y-%m-%d Planning"
    offset: 3
  # Monday week1
  3:
    text: "# %Y-%m-%d Grooming"
    offset: 1
'''

if __name__ == "__main__":
    unittest.main()

# test_agenda.py ends here
