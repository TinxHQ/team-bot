# Team Bot Tools

## agenda.py

`agenda.py` is to be used in a daily crontab to send a message to a
Mattermost channel according to a configuration file.

Example: `./agenda.py planning.yaml $URL 'Dev Daily Scrum'`

`$URL` must be set to the Mattermost webhook URL.
