#!/usr/bin/env python3

import datetime
import unittest
import pytz

from io import StringIO
from unittest.mock import MagicMock, patch

import agenda

CONF = '''
---
period: 21
start: 2020-02-21
old_pr_threshold: 4
recurring_messages:
  - text: 'Daily note on %Y-%m-%d'
  - text: '# %Y-%m-%d'
    before: true
  - text: 'Another before'
    before: true
  - github_old_prs: True
messages:
  # Friday week0
  0:
    text: '- Planning'
    offset: 3
  2:
    offset: 0
  # Monday week1
  3:
    text: '- Grooming'
    offset: 1
'''

MTL_TZ = pytz.timezone('America/Montreal')


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
                    {
                        'github_old_prs': True,
                    },
                ],
                'messages': {
                    0: {'offset': 3, 'text': '- Planning'},
                    2: {'offset': 0},
                    3: {'offset': 1, 'text': '- Grooming'},
                },
                'period': 21,
                'start': datetime.datetime(2020, 2, 21, 0, 0),
                'old_pr_threshold': 4,
            },
        )

    def test_compute_message_with_different_offset(self):
        config = '''
---
period: 3
start: 2022-01-24
recurring_messages:
  - text: '%Y-%m-%d'
messages:
  0:
  1:
    offset: 0
  2:
    offset: 1
        '''
        conf = agenda.load_conf(StringIO(config))
        now = datetime.datetime(2022, 1, 24, 0, 0)
        self.assertEqual(agenda.compute_message(now, conf), '2022-01-24')
        now = datetime.datetime(2022, 1, 25, 0, 0)
        self.assertEqual(agenda.compute_message(now, conf), '2022-01-25')
        now = datetime.datetime(2022, 1, 26, 0, 0)
        self.assertEqual(agenda.compute_message(now, conf), '2022-01-27')

    @patch('agenda.find_oldest_github_prs', MagicMock(return_value=MagicMock(prs=[])))
    @patch('agenda.find_sprint_github_prs', MagicMock(return_value=MagicMock(prs=[])))
    def test_compute_message_no_old_pr(self):
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

    def test_github_filter_age(self):
        montreal_now = datetime.datetime(2020, 2, 21, 15, 0)
        with patch('agenda.montreal_now', montreal_now):
            assert (
                agenda.github_filter_age(minimum_age=0, maximum_age=None)
                == f'updated:*..{montreal_now.isoformat()}'
            )

        montreal_now = datetime.datetime(2020, 2, 21, 15, 0)
        minimum_age = datetime.datetime(2020, 2, 20, 15, 0)
        with patch('agenda.montreal_now', montreal_now):
            assert (
                agenda.github_filter_age(minimum_age=1, maximum_age=None)
                == f'updated:*..{minimum_age.isoformat()}'
            )

        montreal_now = datetime.datetime(2020, 2, 21, 15, 0)
        minimum_age = datetime.datetime(2020, 2, 20, 15, 0)
        maximum_age = datetime.datetime(2020, 2, 18, 15, 0)
        with patch('agenda.montreal_now', montreal_now):
            assert (
                agenda.github_filter_age(minimum_age=1, maximum_age=3)
                == f'updated:{maximum_age.isoformat()}..{minimum_age.isoformat()}'
            )

        # 2020-02-21 is Friday
        montreal_now = datetime.datetime(2020, 2, 21, 15, 0)
        # 6 days ago is Saturday -> skip the weekend (2 days) -> Thursday 2020-02-13
        minimum_age = datetime.datetime(2020, 2, 13, 15, 0)
        # 7 days ago is Friday -> skip the weekend (2 days) -> Wednesday 2020-02-12
        maximum_age = datetime.datetime(2020, 2, 12, 15, 0)
        with patch('agenda.montreal_now', montreal_now):
            assert (
                agenda.github_filter_age(minimum_age=6, maximum_age=7)
                == f'updated:{maximum_age.isoformat()}..{minimum_age.isoformat()}'
            )

    def test_format_pr_list_empty(self):
        assert (
            agenda.format_pr_list(
                oldest_pr_list=MagicMock(prs=[]),
                oldest_query_params=None,
                sprint_pr_list=MagicMock(prs=[]),
                sprint_mergeit_query_params=None,
                sprint_pls_review_query_params=None,
            )
            == []
        )

    def test_format_pr_list(self):
        pr1_date = MTL_TZ.localize(datetime.datetime(2020, 2, 21, 15, 0))
        pr2_date = MTL_TZ.localize(datetime.datetime(2020, 3, 21, 15, 0))
        pr1_age = (MTL_TZ.localize(datetime.datetime.now()) - pr1_date).days
        pr2_age = (MTL_TZ.localize(datetime.datetime.now()) - pr2_date).days
        repository1 = MagicMock()
        repository1.name = 'test_repo'
        repository2 = MagicMock()
        repository2.name = 'test_repo2'
        sprint_pr_list = oldest_pr_list = MagicMock(
            count=2,
            prs=[
                MagicMock(
                    updated_at=pr1_date,
                    title='Test PR',
                    repository=repository1,
                    number=42,
                    html_url='an_url',
                ),
                MagicMock(
                    updated_at=pr2_date,
                    title='Test PR 2',
                    repository=repository2,
                    number=43,
                    html_url='an_url2',
                ),
            ],
        )
        oldest_query_params = ('test',)
        sprint_mergeit_query_params = ('test-mergeit',)
        sprint_pls_review_query_params = ('test-please-review',)
        mergeit_url = 'https://github.com/pulls?q=%28%27test-mergeit%27%2C%29'
        review_url = 'https://github.com/pulls?q=%28%27test-please-review%27%2C%29'
        assert agenda.format_pr_list(
            oldest_pr_list=oldest_pr_list,
            oldest_query_params=oldest_query_params,
            sprint_pr_list=sprint_pr_list,
            sprint_mergeit_query_params=sprint_mergeit_query_params,
            sprint_pls_review_query_params=sprint_pls_review_query_params,
        ) == [
            f'#### Sprint PRs ([mergeit]({mergeit_url}) | [Please review]({review_url}))',
            f'- **{pr1_age} days**: [test_repo #42](an_url) Test PR',
            f'- **{pr2_age} days**: [test_repo2 #43](an_url2) Test PR 2',
            '#### [Old PRs](https://github.com/pulls?q=%28%27test%27%2C%29)',
            f'- **{pr1_age} days**: [test_repo #42](an_url) Test PR',
            f'- **{pr2_age} days**: [test_repo2 #43](an_url2) Test PR 2',
        ]


if __name__ == '__main__':
    unittest.main()
