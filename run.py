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
    t1 = threading.Thread(name="Links", target=app.links)
    t1.daemon = True
    t1.start()
    log.debug("Spawned new thread for link submissions")
    t2 = threading.Thread(name="Comments", target=app.comments)
    t2.daemon = True
    t2.start()
    log.debug("Spawned new thread for comment submissions")

    while True:  # keep main thread running until keyboardinterrupt
        time.sleep(1)

if __name__ == '__main__':
    init()
