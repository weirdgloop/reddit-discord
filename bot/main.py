import configparser
import datetime
import re
import time
import logging
import os

import praw

from .webhook import Webhook

log = logging.getLogger(__name__)

class RedditBot:
    def __init__(self):
        log.info("Loading configuration...")
        self.config = Config('config/config.ini')

        # Make sure the data folder exists
        if not os.path.exists('data'):
            os.makedirs('data')

    def comments(self):
        """Monitors subreddits for comments"""
        reddit = self.create_reddit_instance()
        subs = '+'.join(self.config.reddit_subreddits)
        sub = reddit.subreddit(subs)
        log.info("Monitoring subreddits for comments: {}".format(subs))

        try:
            for c in sub.stream.comments():
                if 'bot' not in c.author.name.lower():  # Ignore bots - this isn't too clean but works mostly
                    rgx_match = re.findall(self.config.target_regex, c.body)
                    if (rgx_match):
                        log.debug('Criteria was matched: {}'.format(rgx_match))
                        comment_time = datetime.datetime.fromtimestamp(c.created)
                        last_time = self.grab_last_time('data/last_comment.txt')

                        if (last_time is None) or (comment_time > last_time):
                            # Handle the comment
                            log.info("New comment: {0} ({0.subreddit.display_name})".format(c))
                            self.handle_comment(c)
        except Exception as e:
            if '503' in str(e):  # Reddit's servers are doing some weird shit
                log.error("Received 503 from Reddit ({}). Waiting before restarting...".format(e))
                time.sleep(30)  # Wait 30 seconds before trying again
                log.warning("Restarting monitoring after 503...")
                self.comments()  # Go again

    def links(self):
        """Monitors subreddits for new posts"""
        reddit = self.create_reddit_instance()
        subs = '+'.join(self.config.reddit_subreddits)
        sub = reddit.subreddit(subs)
        log.info("Monitoring subreddits for posts: {}".format(subs))

        try:
            for post in sub.stream.submissions():
                if 'bot' not in post.author.name.lower():  # Ignore bots - this isn't too clean but works mostly
                    check = [post.url, post.title, post.selftext]

                    matching_rgx = [c for c in check if re.findall(self.config.target_regex, c)]

                    if matching_rgx:  # One or more criteria was matched
                        log.debug('Criteria was matched: {}'.format(matching_rgx))
                        post_time = datetime.datetime.fromtimestamp(post.created)
                        last_time = self.grab_last_time('data/last_submission.txt')

                        if (last_time is None) or (post_time > last_time):
                            log.info("New post: {0.title} ({0.subreddit.display_name})".format(post))
                            self.handle_post(post)
        except Exception as e:
            if '503' in str(e):  # Reddit's servers are doing some weird shit
                log.error("Received 503 from Reddit ({}). Waiting before restarting...".format(e))
                time.sleep(30)  # Wait 30 seconds before trying again
                log.warning("Restarting monitoring after 503...")
                self.links()  # Go again

    def handle_post(self, post):
        """Handles an individual post"""
        if self.config.discord_webhook:
            self.handle_discord(post)
        self.save_last_time('data/last_submission.txt', post.created)

        # TODO: reply to post

    def handle_comment(self, comment):
        """Handles an individual comment"""
        if self.config.discord_webhook:
            self.handle_discord(comment)
        self.save_last_time('data/last_comment.txt', comment.created)

        # TODO: reply to post

    def handle_discord(self, data):
        """Handles the Discord webhooks"""
        embed = Webhook(self.config.discord_webhook, color=16729344)
        embed.set_author(name=data.author.name, icon=data.subreddit.icon_img, url='https://reddit.com/u/{0}'.format(data.author.name))

        if isinstance(data, praw.models.Submission):
            p_type = 'submission'
            url = data.shortlink
            title = data.title
            body = data.selftext if data.is_self else data.url
            thumb = data.thumbnail if not data.is_self else 'https://i.imgur.com/UTOtv5S.png'
        elif isinstance(data, praw.models.Comment):
            p_type = 'comment'
            url = 'https://reddit.com' + data.permalink
            title = data.submission.title
            body = data.body
            thumb = 'https://i.imgur.com/UTOtv5S.png'
        else:
            log.warning('Received data that was not a submission or comment: {0}'.format(data))
            return

        embed.set_title(title='New {0} (/r/{1})'.format(p_type, data.subreddit.display_name), url=url)
        embed.add_field(name='**Title**', value=title, inline=True)
        embed.add_field(name='**Body**', value=body[:750] + (body[750:] and '...'), inline=True)
        embed.set_thumbnail(thumb)
        embed.set_footer(text='Reddit bot by Jayden', ts=True, icon='https://i.imgur.com/S5X2GOw.png')

        e = embed.post()
        return e

    def grab_last_time(self, path):
        """Reads timestamp from a file"""
        log.debug('Grabbing timestamp from {}'.format(path))
        try:
            with open(path) as f:
                ts = f.read()
            if not ts:
                return None

            time = datetime.datetime.fromtimestamp(float(ts))
        except FileNotFoundError:
            log.debug('Creating new file as it does not exist: {}'.format(path))
            open(path, 'a').close()  # Create the file
            return None
        except Exception as e:
            log.error("There was a problem reading the last submission cache file. ({})".format(e))
            return None
        return time

    def save_last_time(self, path, timestamp):
        """Saves timestamp to a file"""
        log.debug('Saving timestamp to {}'.format(path))
        try:
            with open(path, 'w') as f:
                f.write(str(timestamp))
        except Exception as e:
            log.error("There was a problem writing to the last submission cache file. ({})".format(e))
        return True

    def create_reddit_instance(self):
        log.debug('Creating new praw.Reddit instance')
        return praw.Reddit(client_id=self.config.reddit_client_id,
                           client_secret=self.config.reddit_client_secret,
                           user_agent=self.config.reddit_user_agent,
                           username=self.config.reddit_username,
                           password=self.config.reddit_password)

class Config:
    def __init__(self, path):
        self.path = path

        self.c = configparser.ConfigParser()
        log.debug('Attempting to load config from {}'.format(self.path))
        cfile = self.c.read(self.path, encoding='UTF-8')
        if not cfile:  # If the resulting dataset is empty
            raise FileNotFoundError('There is no file at {}'.format(self.path))

        self.load()

    def load(self):
        """Load configuration options"""
        self.reddit_user_agent = 'pc:org.weirdgloop.reddit:v1.0'

        self.reddit_client_id = self.c.get('Auth', 'Reddit-ClientID', fallback=None)
        self.reddit_client_secret = self.c.get('Auth', 'Reddit-ClientSecret', fallback=None)
        self.reddit_username = self.c.get('Auth', 'Reddit-Username', fallback=None)
        self.reddit_password = self.c.get('Auth', 'Reddit-Password', fallback=None)
        self.reddit_subreddits = self.c.get('General', 'Reddit-Subreddits', fallback=None)

        self.discord_webhook = self.c.get('Discord', 'WebhookURL', fallback=None)
        self.target_regex = self.c.get('General', 'TargetRegex', fallback=None)

        self.validate()

    def validate(self):
        """Validates the data provided in the config file"""
        assert self.reddit_client_id, 'No client ID was specified'
        assert self.reddit_client_secret, 'No client secret was specified'
        assert self.reddit_subreddits, 'No subreddits were specified'
        assert self.target_regex, 'No target regex was specified'

        self.reddit_subreddits = self.reddit_subreddits.split()

        log.debug('Using {} as regex pattern'.format(self.target_regex))

        # Optionals
        if self.reddit_username:
            self.reddit_user_agent += ' (u/{})'.format(self.reddit_username)
            log.debug('User agent is now: {}'.format(self.reddit_user_agent))

        if not self.discord_webhook:
            log.warning('No webhook URL provided. Will not log to Discord.')

if __name__ == '__main__':
    raise RuntimeError('This file cannot be executed directly.')
