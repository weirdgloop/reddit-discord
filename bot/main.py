import datetime
import re
import time
import logging
import os
import traceback

import praw

from .webhook import Webhook
from .config import Config

log = logging.getLogger(__name__)

class RedditBot:
    def __init__(self):
        # Make sure the data folder exists
        if not os.path.exists('data'):
            os.makedirs('data')

        log.info("Loading configuration...")
        self.config = Config()
        self.reddit = self.create_reddit_instance()

    def handle_new(self):
        """Monitors subreddits"""
        subs = []
        for h in self.config.hooks:
            subs += h.subreddits
        if not subs:
            raise ValueError('There are no subreddits to monitor')

        subs = '+'.join(set(subs))
        sub = self.reddit.subreddit(subs)
        log.info("Monitoring subreddits: {}".format(subs))

        c_stream = sub.stream.comments(pause_after=0, skip_existing=True)
        s_stream = sub.stream.submissions(pause_after=0, skip_existing=True)

        while True:
            try:
                last_time = datetime.datetime.fromisoformat(self.grab_last_time('data/last_check.txt'))
            except Exception as e:
                last_time = None
            try:
                for c in c_stream:
                    if c is None:
                        break
                    if any(u.lower() == c.author.name.lower() for u in self.config.ignore_list):
                        break
                    for h in self.config.hooks:
                        rgx_match = re.findall(h.regex, c.body)
                        if (rgx_match and str(c.subreddit).lower() in h.subreddits):
                            log.debug('Criteria was matched: {}'.format(rgx_match))
                            comment_time = datetime.datetime.fromtimestamp(c.created_utc)

                            if (last_time is None) or (comment_time > last_time-datetime.timedelta(minutes=5)):
                                # Handle the comment
                                log.info("New comment: {0} ({0.subreddit.display_name})".format(c))
                                self.handle_comment(c, h)
                            else:
                                log.debug('Skipping. Comment time was over 5 mins before last check.')

                for post in s_stream:
                    if post is None:
                        break
                    if any(u.lower() == post.author.name.lower() for u in self.config.ignore_list):
                        break
                    check = [post.url, post.title, post.selftext]

                    for h in self.config.hooks:
                        matching_rgx = [c for c in check if re.findall(h.regex, c)]

                        if (matching_rgx and str(post.subreddit).lower() in h.subreddits):  # One or more criteria was matched
                            log.debug('Criteria was matched: {}'.format(matching_rgx))
                            post_time = datetime.datetime.fromtimestamp(post.created_utc)

                            if (last_time is None) or (post_time > last_time-datetime.timedelta(minutes=5)):
                                log.info("New post: {0.title} ({0.subreddit.display_name})".format(post))
                                self.handle_post(post, h)
                            else:
                                log.debug('Skipping. Post time was over 5 mins before last check.')
            
                self.save_last_time('data/last_check.txt', datetime.datetime.utcnow())

            except Exception as e:
                if '503' in str(e):  # Reddit's servers are doing some weird shit
                    log.error("Received 503 from Reddit ({}). Waiting before restarting...".format(e))
                    time.sleep(30)  # Wait 30 seconds before trying again
                    log.warning("Restarting monitoring after 503...")
                else:
                    log.error("An error occurred: {0}\n".format(e, traceback.format_exc()))
                self.handle_new()  # Go again

    def handle_post(self, post, hook):
        """Handles an individual post"""
        if hook.url:
            self.handle_discord(post, hook.url)

    def handle_comment(self, comment, hook):
        """Handles an individual comment"""
        if hook.url:
            self.handle_discord(comment, hook.url)

    def handle_discord(self, data, url):
        """Handles the Discord webhooks"""
        embed = Webhook(url, color=16729344)
        embed.set_author(name=data.author.name, icon=data.subreddit.icon_img, url='https://reddit.com/u/{0}'.format(data.author.name))

        if isinstance(data, praw.models.Submission):
            p_type = 'submission'
            url = data.shortlink
            title = data.title
            body = data.selftext if data.is_self else data.url
            thumb = data.thumbnail if not data.is_self else self.config.sub_thumb
        elif isinstance(data, praw.models.Comment):
            p_type = 'comment'
            url = 'https://reddit.com' + data.permalink + '?context=1000'
            title = data.submission.title
            body = data.body
            thumb = self.config.comment_thumb
        else:
            log.warning('Received data that was not a submission or comment: {0}'.format(data))
            return

        embed.set_title(title='New {0} (/r/{1})'.format(p_type, data.subreddit.display_name), url=url)
        embed.add_field(name='**Title**', value=title, inline=True)
        embed.add_field(name='**Body**', value=body[:750] + (body[750:] and '...'), inline=True)
        embed.set_thumbnail(thumb)
        embed.set_footer(text=self.config.footer_text, ts=True, icon=self.config.footer_icon)

        e = embed.post()
        return e

    def grab_last_time(self, path):
        """Reads timestamp from a file"""
        try:
            ts = None
            with open(path) as f:
                ts = str(f.read())
            return ts
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
        try:
            with open(path, 'w') as f:
                f.write(str(timestamp))
        except Exception as e:
            log.error("There was a problem writing to the last submission cache file. ({})".format(e))
        return True

    def create_reddit_instance(self):
        log.debug('Creating new praw.Reddit instance')
        return praw.Reddit(client_id=self.config.reddit_clientid,
                           client_secret=self.config.reddit_clientsecret,
                           user_agent=self.config.reddit_useragent,
                           username=self.config.reddit_username,
                           password=self.config.reddit_password)

if __name__ == '__main__':
    raise RuntimeError('This file cannot be executed directly.')
