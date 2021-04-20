#!/usr/bin/env python3

import datetime
import unittest

from io import StringIO

import agenda


class TestAgenda(unittest.TestCase):
    def test_load_conf(self):
        self.assertEqual(
            agenda.load_conf(StringIO(CONF)),
            {
                'recurring_messages': [
                    {
                        'text': 'Daily note on %Y-%m-%d',
                    },
                    {
                        'text': '# %Y-%m-%d',
                        'before': True,
                    },
                    {
                        'text': 'Another before',
                        'before': True,
                    },
                ],
                'messages': {
                    0: {'offset': 3, 'text': '- Planning'},
                    2: {'offset': 0},
                    3: {'offset': 1, 'text': '- Grooming'},
                },
                'period': 21,
                'start': datetime.datetime(2020, 2, 21, 0, 0),
            },
        )

    def test_compute_message(self):
        conf = agenda.load_conf(StringIO(CONF))
        now = datetime.datetime(2020, 2, 21, 17, 0)
        self.assertEqual(
            agenda.compute_message(now, conf),
            '# 2020-02-24\nAnother before\n- Planning\nDaily note on 2020-02-24',
        )
        now = datetime.datetime(2020, 2, 22, 17, 0)
        self.assertEqual(agenda.compute_message(now, conf), None)
        now = datetime.datetime(2020, 2, 23, 17, 0)
        self.assertEqual(
            agenda.compute_message(now, conf),
            '# 2020-02-23\nAnother before\nDaily note on 2020-02-23',
        )
        now = datetime.datetime(2020, 2, 24, 17, 0)
        self.assertEqual(
            agenda.compute_message(now, conf),
            '# 2020-02-25\nAnother before\n- Grooming\nDaily note on 2020-02-25',
        )


CONF = '''
---
period: 21
start: 2020-02-21
recurring_messages:
  - text: "Daily note on %Y-%m-%d"
  - text: "# %Y-%m-%d"
    before: true
  - text: "Another before"
    before: true
messages:
  # Friday week0
  0:
    text: "- Planning"
    offset: 3
  2:
    offset: 0
  # Monday week1
  3:
    text: "- Grooming"
    offset: 1
'''

if __name__ == "__main__":
    unittest.main()
