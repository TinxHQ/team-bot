#!/usr/bin/env python3

import github3
import os
import requests
import sys
import yaml

from datetime import timedelta, datetime

GITHUB_SEARCH_QUERY = r'is:open is:pr archived:false user:wazo-platform user:TinxHQ user:wazo-communication sort:updated-asc label:mergeit label:"🙏 Please review"'
MAX_SEARCH = 10

GITHUB_USER = os.getenv('GITHUB_CREDS_USR')
GITHUB_PASSWORD = os.getenv('GITHUB_CREDS_PSW')


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
                message_lines.extend(find_old_github_prs(conf['old_pr_threshold']))

    message_lines = before_message_lines + message_lines
    if message_lines:
        return "\n".join(message_lines)
    return None


def get_github_prs(github, search_query):
    return [
        result.issue.pull_request()
        for result in github.search_issues(search_query, number=MAX_SEARCH)
    ]


def find_old_github_prs(day_threshold):
    github = github3.GitHub(GITHUB_USER, GITHUB_PASSWORD)
    prs = get_github_prs(github, GITHUB_SEARCH_QUERY)
    old_prs = []
    for pr in prs:
        updated = pr.updated_at
        age = (datetime.now() - updated).days
        if age >= day_threshold:
            line = f'- **{age} days**: [{pr.title} ({pr.repository.fullname}#{pr.number})]({pr.html_url})'
            old_prs.append(line)
    if not old_prs:
        old_prs.append('- None, congratulations!')
    return old_prs


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
