#!/usr/bin/env python3

import requests
import sys
import yaml

from datetime import (timedelta, datetime)


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
    if idx in conf['messages']:
        data = conf['messages'][idx]
        new_date = today + timedelta(data['offset'])
        msg = new_date.strftime(data['text'])
        return msg
    return None


if __name__ == "__main__":
    try:
        conf_file_path = sys.argv[1]
        mattermost_url = sys.argv[2]
        mattermost_channel = sys.argv[3]
    except IndexError:
        print('Usage: %s <conf> <url> <chan>' % sys.argv[0], file=sys.stderr)
        sys.exit(1)

    conf = load_conf(open(conf_file_path))
    now = datetime.now()
    message = compute_message(now, conf)
    if message:
        print(message, mattermost_channel, file=sys.stderr)
        send_message(mattermost_url, message, mattermost_channel)
    else:
        print('No message today', file=sys.stderr)
