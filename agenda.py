#!/usr/bin/env python3

import github3
import itertools
import os
import pytz
import requests
import sys
import yaml

from datetime import timedelta, datetime

GITHUB_SEARCH_QUERY_PARTS = [
    'is:open',
    'is:pr',
    'archived:false',
    'user:wazo-platform',
    'user:TinxHQ',
    'user:wazo-communication',
    'sort:updated-asc',
    'draft:false',
    '-author:app/dependabot',
]

GITHUB_USER = os.getenv('GITHUB_CREDS_USR')
GITHUB_PASSWORD = os.getenv('GITHUB_CREDS_PSW')

MAX_PR_COUNT_DISPLAYED = 10


def send_message(url, message, channel=None):
    headers = {'Content-Type': 'application/json'}
    msg = "\n".join(message.split('\\n'))
    data = {'text': msg}
    if channel:
        data['channel'] = channel
    resp = requests.post(url, headers=headers, json=data)
    resp.raise_for_status()
    return resp


def load_conf(stream):
    data = yaml.safe_load(stream)
    data['start'] = datetime.strptime(str(data['start']), '%Y-%m-%d')
    return data


def compute_message(today, conf):
    delta = today - conf['start']
    idx = delta.days % conf['period']
    before_message_lines = []
    message_lines = []
    if idx in conf['messages']:
        data = conf['messages'][idx]
        new_date = today + timedelta(data['offset'])
        if data.get('text'):
            msg = new_date.strftime(data['text'])
            message_lines.append(msg)
        if conf['recurring_messages']:
            for recurring_msg in conf['recurring_messages']:
                list_to_append = (
                    before_message_lines
                    if recurring_msg.get('before')
                    else message_lines
                )
                list_to_append.append(new_date.strftime(recurring_msg['text']))

            if recurring_msg.get('github_old_prs'):
                minimum_age = conf['old_pr_threshold']
                mtl_tz = pytz.timezone('America/Montreal')
                mtl_time = mtl_tz.localize(datetime.now())
                pr_list = find_old_github_prs(mtl_time, minimum_age)
                pr_message_lines = format_pr_list(pr_list, mtl_time, conf['period'])
                message_lines.extend(pr_message_lines)

    message_lines = before_message_lines + message_lines
    if message_lines:
        return "\n".join(message_lines)
    return None


def get_github_prs(github, search_query):
    return [
        result.issue.pull_request()
        for result in github.search_issues(search_query)
    ]


def generate_github_query_params(now_time, day_threshold):
    search_date = now_time - timedelta(days=day_threshold)
    search_date_iso = search_date.isoformat()
    query = GITHUB_SEARCH_QUERY_PARTS + [f'updated:<{search_date_iso}']
    return ' '.join(query)


def find_old_github_prs(mtl_time, day_threshold):
    github = github3.GitHub(GITHUB_USER, GITHUB_PASSWORD)
    query_params = generate_github_query_params(mtl_time, day_threshold)
    prs = get_github_prs(github, query_params)
    return prs


def partition(pred, iterable):
    "Use a predicate to partition entries into false entries and true entries"
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    # Source: https://docs.python.org/3/library/itertools.html
    t1, t2 = itertools.tee(iterable)
    return itertools.filterfalse(pred, t1), filter(pred, t2)


def format_pr_list(pr_list, mtl_time, period):
    def pr_age(pr):
        return (mtl_time - pr.updated_at).days

    def pr_in_period(pr):
        return pr_age(pr) < period

    older_pr_gen, period_pr_gen = partition(pr_in_period, pr_list)
    older_pr_list = list(older_pr_gen)
    period_pr_list = list(period_pr_gen)

    message_lines = []

    if older_pr_list:
        message_lines.append(f'- PR older than {period} days: {len(older_pr_list)}')

    for pr in period_pr_list[:MAX_PR_COUNT_DISPLAYED]:
        line = f'- **{pr_age(pr)} days**: [{pr.title} ({pr.repository.full_name}#{pr.number})]({pr.html_url})'
        message_lines.append(line)

    return message_lines


if __name__ == "__main__":
    try:
        conf_file_path = sys.argv[1]
        mattermost_url = sys.argv[2]
        mattermost_channel = sys.argv[3]
    except IndexError:
        print('Usage: %s <conf> <url> <chan>' % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    with open(conf_file_path, 'r') as conf_file:
        conf = load_conf(conf_file)
    now = datetime.now()
    message = compute_message(now, conf)
    if message:
        print(message, mattermost_channel, file=sys.stderr)
        send_message(mattermost_url, message, mattermost_channel)
    else:
        print('No message today', file=sys.stderr)
