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

        self.targets = ['wikia', 'runescape.wikia.com', 'oldschoolrunescape.wikia.com']
        self.targets_regex = r"(wiki)\b"

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
                if 'bot' not in c.author.name:  # Ignore bots - this isn't too clean but works mostly
                    if (any(t in c.body for t in self.targets) or re.match(self.targets_regex, c.body)):
                        comment_time = datetime.datetime.fromtimestamp(c.created)
                        last_time = self.grab_last_time('data/last_comment.txt')

                        if (last_time is None) or (comment_time > last_time):
                            # Handle the comment
                            log.info("Detected a new comment: {0} ({0.subreddit.display_name})".format(c))
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
                if 'bot' not in post.author.name:  # Ignore bots - this isn't too clean but works mostly
                    # Check that the submission is more recent than the last one
                    post_time = datetime.datetime.fromtimestamp(post.created)

                    if post.is_self:
                        last_time = self.grab_last_time('data/last_text_submission.txt')
                    else:
                        last_time = self.grab_last_time('data/last_link_submission.txt')

                    check = [post.url, post.title, post.selftext]

                    if (last_time is None) or (post_time > last_time):
                        matching = [c for c in check if any(t in c for t in self.targets)]
                        matching_rgx = [c for c in check if re.findall(self.targets_regex, c)]

                        if matching or matching_rgx:  # One or more criteria was matched
                            if post.is_self:
                                log.info("New self post: {0.title} ({0.subreddit.display_name})".format(post))
                                self.handle_text(post)
                            else:
                                log.info("New link post: {0.title} ({0.subreddit.display_name})".format(post))
                                self.handle_link(post)
        except Exception as e:
            if '503' in str(e):  # Reddit's servers are doing some weird shit
                log.error("Received 503 from Reddit ({}). Waiting before restarting...".format(e))
                time.sleep(30)  # Wait 30 seconds before trying again
                log.warning("Restarting monitoring after 503...")
                self.links()  # Go again

    def handle_text(self, post):
        e = self.generate_text_post_embed(post)  # Create a Discord embed
        e.post()  # POST to Discord webhook
        self.save_last_time('data/last_text_submission.txt', post.created)

    def handle_link(self, post):
        e = self.generate_link_post_embed(post)  # Create a Discord embed
        e.post()  # POST to Discord webhook
        self.save_last_time('data/last_link_submission.txt', post.created)

    def handle_comment(self, comment):
        e = self.generate_comment_embed(comment)  # Create a Discord embed
        e.post()  # POST to Discord webhook
        self.save_last_time('data/last_comment.txt', comment.created)

    def generate_text_post_embed(self, post):
        embed = Webhook(self.config.discord_webhook, color=1146810)
        embed.set_author(name=post.author.name, icon=post.subreddit.icon_img, url='https://reddit.com/u/{}'.format(post.author.name))
        embed.set_title(title='New text post on /r/{}'.format(post.subreddit.display_name), url=post.shortlink)
        embed.add_field(name='**Title**', value='{}'.format(post.title), inline=True)
        embed.add_field(name='**Post**', value=post.selftext[:150] + (post.selftext[150:] and '...'), inline=True)
        embed.set_thumbnail('https://i.imgur.com/UTOtv5S.png')
        return embed

    def generate_link_post_embed(self, post):
        embed = Webhook(self.config.discord_webhook, color=1146810)
        embed.set_author(name=post.author.name, icon=post.subreddit.icon_img, url='https://reddit.com/u/{}'.format(post.author.name))
        embed.set_title(title='New link post on /r/{}'.format(post.subreddit.display_name), url=post.shortlink)
        embed.add_field(name='**Title**', value='{}'.format(post.title), inline=True)
        embed.add_field(name='**Links to**', value=post.url, inline=True)
        embed.set_thumbnail(post.thumbnail)
        return embed

    def generate_comment_embed(self, comment):
        permalink = 'https://reddit.com' + comment.permalink
        embed = Webhook(self.config.discord_webhook, color=1146810)
        embed.set_author(name=comment.author.name, icon=comment.subreddit.icon_img, url='https://reddit.com/u/{}'.format(comment.author.name))
        embed.set_title(title='Mentioned in a comment on /r/{}'.format(comment.subreddit.display_name), url=permalink)
        embed.add_field(name='**Thread**', value='{}'.format(comment.submission.title), inline=True)
        embed.add_field(name='**Comment**', value=comment.body[:150] + (comment.body[150:] and '...'), inline=True)
        embed.set_thumbnail('https://i.imgur.com/UTOtv5S.png')
        return embed

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

        self.validate()

    def validate(self):
        assert self.reddit_client_id, 'No client ID was specified'
        assert self.reddit_client_secret, 'No client secret was specified'
        assert self.reddit_subreddits, 'No subreddits were specified'

        self.reddit_subreddits = self.reddit_subreddits.split()

        if self.reddit_username:
            self.reddit_user_agent += ' (u/{})'.format(self.reddit_username)
            log.debug('User agent is now: {}'.format(self.reddit_user_agent))

if __name__ == '__main__':
    raise RuntimeError('This file cannot be executed directly.')
