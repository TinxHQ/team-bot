#!/usr/bin/env python3

import github3
import operator
import os
import pytz
import requests
import urllib
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

MAX_PR_COUNT_DISPLAYED = 5
SPRINT_MAX_AGE = 21
OLDEST_PR_MIN_AGE = 30

MONTREAL_TIMEZONE = pytz.timezone('America/Montreal')
montreal_now = MONTREAL_TIMEZONE.localize(datetime.now())


class PRList:
    def __init__(self, prs, count):
        self.prs = prs
        self.count = count


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
        if conf.get('recurring_messages'):
            for recurring_msg in conf['recurring_messages']:
                list_to_append = (
                    before_message_lines
                    if recurring_msg.get('before')
                    else message_lines
                )
                if recurring_msg.get('text'):
                    list_to_append.append(new_date.strftime(recurring_msg['text']))

            if recurring_msg.get('github_old_prs'):
                minimum_age = conf['old_pr_threshold']
                oldest_pr_list = find_oldest_github_prs(OLDEST_PR_MIN_AGE)
                sprint_pr_list = find_sprint_github_prs(minimum_age)
                oldest_query_params = generate_oldest_pr_github_query_params(
                    OLDEST_PR_MIN_AGE
                )
                sprint_mergeit_query_params = (
                    generate_sprint_mergeit_github_query_params(minimum_age)
                )
                sprint_pls_review_query_params = (
                    generate_sprint_pls_review_github_query_params(minimum_age)
                )
                pr_message_lines = format_pr_list(
                    oldest_pr_list,
                    oldest_query_params,
                    sprint_pr_list,
                    sprint_mergeit_query_params,
                    sprint_pls_review_query_params,
                )
                message_lines.extend(pr_message_lines)

    message_lines = before_message_lines + message_lines
    if message_lines:
        return "\n".join(message_lines)
    return None


def get_github_prs(github, search_query, limit):
    return [
        result.issue.pull_request()
        for result in github.search_issues(search_query, number=limit)
    ]


def count_github_prs(github, search_query):
    return len(list(github.search_issues(search_query)))


def github_filter_age(minimum_age, maximum_age=None):
    def minimum_open_days(days):
        if days >= montreal_now.isoweekday():
            return days + 2  # skip saturday + sunday of the last week-end
        return days

    date_range = maximum_age - minimum_age if maximum_age else 0
    minimum_age_open_days = minimum_open_days(minimum_age)
    latest_date = (montreal_now - timedelta(days=minimum_age_open_days)).isoformat()

    open_range = minimum_age_open_days + date_range
    earliest_date_from_now = (montreal_now - timedelta(days=open_range)).isoformat()
    earliest_date = '*' if not maximum_age else earliest_date_from_now

    return f'updated:{earliest_date}..{latest_date}'


def github_query_params(filters):
    return ' '.join(filters)


def generate_oldest_pr_github_query_params(minimum_age):
    return github_query_params(
        GITHUB_SEARCH_QUERY_PARTS + [github_filter_age(minimum_age), '-label:Blocked']
    )


def find_oldest_github_prs(minimum_age):
    github = github3.GitHub(GITHUB_USER, GITHUB_PASSWORD)
    query_params = generate_oldest_pr_github_query_params(minimum_age)
    prs = get_github_prs(github, query_params, MAX_PR_COUNT_DISPLAYED)
    count = count_github_prs(github, query_params)
    return PRList(prs, count)


def generate_sprint_mergeit_github_query_params(minimum_age):
    return github_query_params(
        GITHUB_SEARCH_QUERY_PARTS
        + [github_filter_age(minimum_age, SPRINT_MAX_AGE), 'label:mergeit']
    )


def generate_sprint_pls_review_github_query_params(minimum_age):
    return github_query_params(
        GITHUB_SEARCH_QUERY_PARTS
        + [github_filter_age(minimum_age, SPRINT_MAX_AGE), 'label:"🙏 Please review"']
    )


def find_sprint_github_prs(minimum_age):
    github = github3.GitHub(GITHUB_USER, GITHUB_PASSWORD)
    query_params = generate_sprint_mergeit_github_query_params(minimum_age)
    mergeit_prs = get_github_prs(github, query_params, MAX_PR_COUNT_DISPLAYED)
    mergeit_count = count_github_prs(github, query_params)
    query_params = generate_sprint_pls_review_github_query_params(minimum_age)
    please_review_prs = get_github_prs(github, query_params, MAX_PR_COUNT_DISPLAYED)
    please_review_count = count_github_prs(github, query_params)
    prs = sorted(mergeit_prs + please_review_prs, key=operator.attrgetter("updated_at"))
    count = mergeit_count + please_review_count
    return PRList(prs, count)


def format_pr_list(
    oldest_pr_list,
    oldest_query_params,
    sprint_pr_list,
    sprint_mergeit_query_params,
    sprint_pls_review_query_params,
):
    def pr_age(pr):
        return (montreal_now - pr.updated_at).days

    def pr_list_url(query_params):
        query_string = urllib.parse.urlencode({'q': query_params})
        return f'https://github.com/pulls?{query_string}'

    message_lines = []

    if sprint_pr_list.prs:
        count = sprint_pr_list.count
        count = '' if count < MAX_PR_COUNT_DISPLAYED else f'{count} '
        mergeit_url = pr_list_url(sprint_mergeit_query_params)
        review_url = pr_list_url(sprint_pls_review_query_params)
        message_lines.append(
            f'#### {count}Sprint PRs ([mergeit]({mergeit_url}) | [Please review]({review_url}))'
        )
        for pr in sprint_pr_list.prs[:MAX_PR_COUNT_DISPLAYED]:
            line = f'- **{pr_age(pr)} days**: [{pr.repository.name} #{pr.number}]({pr.html_url}) {pr.title}'
            message_lines.append(line)

    if oldest_pr_list.prs:
        count = oldest_pr_list.count
        count = '' if count < MAX_PR_COUNT_DISPLAYED else f'{count} '
        message_lines.append(
            f'#### [{count}Old PRs]({pr_list_url(oldest_query_params)})'
        )
        for pr in oldest_pr_list.prs[:MAX_PR_COUNT_DISPLAYED]:
            line = f'- **{pr_age(pr)} days**: [{pr.repository.name} #{pr.number}]({pr.html_url}) {pr.title}'
            message_lines.append(line)

    return message_lines


if __name__ == "__main__":
    try:
        conf_file_path = sys.argv[1]
        mattermost_url = sys.argv[2]
        mattermost_channels = sys.argv[3:]
    except IndexError:
        print('Usage: %s <conf> <url> <chan>' % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    with open(conf_file_path, 'r') as conf_file:
        conf = load_conf(conf_file)
    now = datetime.now()
    message = compute_message(now, conf)
    if message:
        for mattermost_channel in mattermost_channels:
            print(message, mattermost_channel, file=sys.stderr)
            send_message(mattermost_url, message, mattermost_channel)
    else:
        print('No message today', file=sys.stderr)
