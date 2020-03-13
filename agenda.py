#!/usr/bin/env python

'''
'''

from datetime import (timedelta, datetime)
import json
import requests
import sys
import yaml


def send_message(url, message, channel=None):
    msg = "\n".join(message.split('\\n'))
    data = {'text': msg}
    if channel:
        data['channel'] = channel
    resp = requests.post(url, data=json.dumps(data))
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
    if len(sys.argv) != 4:
        print('Usage: %s <conf> <url> <chan>' % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    conf = load_conf(open(sys.argv[1]))
    now = datetime.now()
    message = compute_message(now, conf)
    if message:
        print(message, sys.argv[3], file=sys.stderr)
        send_message(sys.argv[2], message, sys.argv[3])
    else:
        print('No message today', file=sys.stderr)

# agenda.py ends here
