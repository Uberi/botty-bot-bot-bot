botty-bot-bot-bot
=================
Chatbot and utilities for Slack using the Slack Realtime Messaging API.

Files
-----

### `example-download-history.sh`, `download-history.py`

`download-history.py` downloads history from all channels in the Slack team associated with a given API token. If previously downloaded history is present, the new history will be seamlessly and transparently added to the old history.

`example-download-history.sh` is a Bash script that shows a sample usage of `download-history.py`. If you edit the script to replace `SLACK_API_TOKEN_GOES_HERE` with an actual API token, you can download history simply by running that.

    $ python3 download-history.py
    Usage: download-history.py SLACK_API_TOKEN [SAVE_FOLDER]
        SLACK_API_TOKEN    Slack API token (obtainable from https://api.slack.com/tokens)
        SAVE_FOLDER        Folder to save messages in (defaults to @history)
