import json
import os
import logging
import re

log = logging.getLogger(__name__)

JSON_FILE = 'config/config.json'

class Config:
    def __init__(self):
        # Check config file exists
        if not os.path.isfile(JSON_FILE):
            raise FileNotFoundError('The config file could not be found.')

        # Try to load it as JSON
        with open(JSON_FILE) as f:
            data = json.load(f)

        self.json = data
        self.validate(data)

    def validate(self, data):
        # Get all top-level keys to check structure
        keys = data.keys()
        if not set(keys).issuperset(set(['hooks', 'reddit'])):
            raise ValueError('Config file is missing one or more required sections.')

        # Get some basic data
        self.default_regex = data.get('default_regex', '')
        if self.default_regex:
            self.default_regex = re.compile(self.default_regex)

        reddit = data.get('reddit', {})
        self.reddit_clientid = reddit.get('client_id', '')
        self.reddit_clientsecret = reddit.get('client_secret', '')
        if not self.reddit_clientid or not self.reddit_clientsecret:
            raise ValueError('A reddit client ID and client secret are required to run this app')
        self.reddit_useragent = reddit.get('client_ua', 'pc:org.weirdgloop.reddit:v1.1'),
        self.reddit_username = reddit.get('username', '')
        self.reddit_password = reddit.get('password', '')

        # Create a new object for each hook
        hooks = []
        for h in data['hooks']:
            try:
                h_obj = Hook(**h)
                if h_obj.regex is None:
                    h_obj.regex = self.default_regex
                hooks.append(h_obj)
            except Exception as e:
                log.error('One of the hooks in the config had an issue: {0}'.format(e))
        if not hooks:
            raise IndexError('There are no valid hooks to use')
        self.hooks = hooks

class Hook:
    def __init__(self, **kwargs):
        self.url = kwargs.get('url', None)
        if not self.url:
            raise ValueError('A webhook in the config does not have a URL specified')
        self.subreddits = kwargs.get('subreddits', [])
        self.regex = kwargs.get('regex', None)
        if self.regex:
            self.regex = re.compile(self.regex)

if __name__ == '__main__':
    raise RuntimeError('This file cannot be executed directly.')
