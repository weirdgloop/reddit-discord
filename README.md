## reddit
This repository is for a multi-purpose Reddit bot that is intended for use for the RuneScape and Old School RuneScape wikis. As it is inevitable that people may link to the old locations of the wikis on Wikia, this bot will reply to those posts and comments with the correct link to the appropiate wiki. In addition, all comments and posts matching a certain criteria or regular expression will be logged to a Discord channel via a webhook.

### Dependencies
* Python 3.5+ (developed using 3.6)
* `praw` for interacting with the Reddit API
* `colorlog` for logging in colour to the console

These dependencies can be installed by running `pip install -U -r requirements.txt` in the base folder of the repo.

### Configuration
An example configuration file is provided in `config/config.empty.ini`. This file should be copied to `config.ini` in the same folder and filled in. It is required for you to enter your Reddit client ID, client secret, and the appropiate subreddits you want to track for the bot's basic functionality to work. Most of these details can be obtained from https://www.reddit.com/prefs/apps/, which requires creating a new application. For more information about configuration options, see the comments inside the example file.

### Running
Use `python run.py` to start the bot after filling in the configuration file.