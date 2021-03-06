import logging
import threading
import time

import colorlog

import bot

# Init logging
l_h = colorlog.StreamHandler()
l_h.setFormatter(colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)s:%(name)s: %(message)s',
    log_colors={
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'red',
    },
))
log = logging.getLogger('bot')
log.addHandler(l_h)
log.setLevel(logging.DEBUG)

def init():
    app = bot.RedditBot()
    app.handle_new()
if __name__ == '__main__':
    init()
