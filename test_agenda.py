#!/usr/bin/env python3

import datetime
import unittest

from io import StringIO
from unittest.mock import MagicMock, patch

import agenda

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

    @patch('agenda.get_github_prs')
    def test_github_only_one_old_pr(self, github_results):
        pr_date = datetime.datetime(2020, 2, 21, 15, 0)
        github_results.return_value = [
            MagicMock(
                updated_at=pr_date,
                title='Test PR',
                repository=MagicMock(fullname='test/test_repo'),
                number=42,
                html_url='an_url',
            ),
        ]
        prs = agenda.find_old_github_prs()
        age = (datetime.datetime.now() - pr_date).days
        expected_lines = [f'- **{age} days**: [Test PR (test/test_repo#42)](an_url)']
        self.assertEqual(prs, expected_lines)

    @patch('agenda.get_github_prs')
    def test_github_multiple_old_prs(self, github_results):
        pr1_date = datetime.datetime(2020, 2, 21, 15, 0)
        pr2_date = datetime.datetime(2020, 3, 21, 15, 0)
        github_results.return_value = [
            MagicMock(
                updated_at=pr1_date,
                title='Test PR',
                repository=MagicMock(fullname='test/test_repo'),
                number=42,
                html_url='an_url',
            ),
            MagicMock(
                updated_at=pr2_date,
                title='Test PR 2',
                repository=MagicMock(fullname='test/test_repo2'),
                number=43,
                html_url='an_url2',
            ),
        ]
        prs = agenda.find_old_github_prs()
        pr1_age = (datetime.datetime.now() - pr1_date).days
        pr2_age = (datetime.datetime.now() - pr2_date).days
        expected_lines = [
            f'- **{pr1_age} days**: [Test PR (test/test_repo#42)](an_url)',
            f'- **{pr2_age} days**: [Test PR 2 (test/test_repo2#43)](an_url2)',
        ]
        self.assertEqual(prs, expected_lines)

    @patch('agenda.get_github_prs')
    def test_github_no_old_pr(self, github_results):
        github_results.return_value = []
        prs = agenda.find_old_github_prs()
        expected_lines = []
        self.assertEqual(prs, expected_lines)


if __name__ == "__main__":
    unittest.main()
