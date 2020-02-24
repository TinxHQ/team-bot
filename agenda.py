#!/usr/bin/env python

'''
'''

from datetime import (timedelta, datetime)
import json
import requests
import sys
import yaml


def json_message(message, channel=None):
    data = {'text': message}
    if channel:
        data['channel'] = channel
    return json.dumps(data)


def send_message(data, url):
    requests.post(url, data=data)


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
    if len(sys.argv) != 4:
        print('Usage: %s <conf> <url> <chan>' % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    conf = load_conf(open(sys.argv[1]))
    now = datetime.now()
    message = compute_message(now, conf)
    if message:
        print(message, sys.argv[3], file=sys.stderr)
        data = json_message(message, sys.argv[3])
        send_message(data, sys.argv[2])
    else:
        print('No message today', file=sys.stderr)

# agenda.py ends here
