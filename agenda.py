#!/usr/bin/env python3

import requests
import sys
import yaml

from datetime import timedelta, datetime


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
    message_lines = before_message_lines + message_lines
    if message_lines:
        return "\n".join(message_lines)
    return None


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
