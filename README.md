## reddit
This repository is for a Reddit bot for Discord used by the RuneScape Wiki server. All comments and posts matching a certain criteria or regular expression will be logged to a Discord channel via a webhook.

### Dependencies
* Python 3.5+ (developed using 3.6)
* `praw` for interacting with the Reddit API
* `colorlog` for logging in colour to the console

These dependencies can be installed by running `pip install -U -r requirements.txt` in the base folder of the repo.

### Configuration
An example configuration file is provided in `config/config.empty.ini`. This file should be copied to `config.ini` in the same folder and filled in. It is required for you to enter your Reddit client ID, client secret, the target regex, and the appropiate subreddits you want to track for the bot's basic functionality to work. Most of these details can be obtained from https://www.reddit.com/prefs/apps/, which requires creating a new application. For more information about configuration options, see the comments inside the example file.

For the target regular expression, this can be used to match queries about both the RuneScape and Old School RuneScape wiki:

```
(wiki(?![\w/])|wikia(?![\w.])|runescape\.wikia\.com|oldschoolrunescape\.wikia\.com)
```

### Running
Use `python run.py` to start the bot after filling in the configuration file.