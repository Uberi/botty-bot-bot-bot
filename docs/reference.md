Code Reference
==============

Plugin API
----------

Plugins inherit a number of methods from the `BasePlugin` class in `src/plugins/utilities.py`:

* `self.untag_word(word)` - returns the word `word` where characters are replaced with Unicode homoglyphs such that they are unlikely to highlight users.
    * Useful for if you want to send a user's name without highlighting them.
* `self.get_message_text(message)` - returns the text value of `message` if it is a valid text message, or `None` otherwise.
* `self.get_message_timestamp(message)` - returns the timestamp of `message` if there is one, or `None` otherwise.
* `self.get_message_channel(message)` - returns the ID of the channel containing `message` if there is one, or `None` otherwise.
* `self.get_message_sender(message)` - returns the ID of the user who sent `message` if there is one, or `None` otherwise.
* `self.say(channel_id, sendable_text)` - send a message containing `sendable_text` to the channel with ID `channel_id`.
    * `sendable_text` must be sendable text (see "Types of Text" for details).
    * Plain text can be converted into sendable text using `self.text_to_sendable_text`.
    * Returns a message ID (used internally, unique to every `SlackBot` instance).
* `self.say_raw(channel_id, text)` - same as `self.say`, but `text` is plain text instead of sendable text.
* `self.say_complete(channel_id, text)` and `self.say_complete(channel_id, text)` - same as `self.say` and `self.say_raw`, but waits for the message to fully send before returning.
    * Returns the message timestamp.
    * Raises a `TimeoutError` if sending times out, or a `ValueError` if sending fails.
* `self.respond(sendable_text)` - does the same thing as `self.say`, but always sends the message to the channel of the message we most recently processed.
    * If this is called within an `on_message(message)` handler, the message will always be sent to the same channel as the one containing `message`.
* `self.respond_raw(text)` - same as `self.respond`, but `text` is plain text instead of sendable text.
* `self.respond_complete(sendable_text)` and `self.respond_raw_complete(text)` - same as `self.respond` and `self.respond_raw`, but waits for the message to fully send before returning.
    * Returns the message timestamp.
    * Raises a `TimeoutError` if sending times out, or a `ValueError` if sending fails.
* `react(channel_id, timestamp, emoticon)` - react with `emoticon` to the message with timestamp `timestamp` in channel with ID `channel_id`.
* `unreact(channel_id, timestamp, emoticon)` - unreact with `emoticon` to the message with timestamp `timestamp` in channel with ID `channel_id`.
* `reply(emoticon)` - react with `emoticon` to the most recently received message.
    * If this is called within an `on_message(message)` handler, the reaction will be to `message`.
* `unreply(emoticon)` - unreact with `emoticon` to the most recently received message.
    * If this is called within an `on_message(message)` handler, the reaction will be to `message`.
* `self.get_channel_name_by_id(channel_id)` - returns the name of the channel with ID `channel_id`, or `None` if there are no channels with that ID. Channels include public channels, direct messages with other users, and private groups.
    * Channels include public channels, direct messages with other users, and private groups.
* `self.get_channel_id_by_name(channel_name)` - returns the ID of the channel with name `channel_name`, or `None` if there are no channels with that name. Channels include public channels, direct messages with other users, and private groups.
    * Channels include public channels, direct messages with other users, and private groups.
* `self.get_user_name_by_id(user_id)` - returns the username of the user with ID `user_id`, or `None` if there are no users with that ID.
* `self.get_user_id_by_name(user_id)` - returns the ID of the user with username `user_name`, or `None` if there are no users with that username.
* `self.get_direct_message_channel_id_by_user_id(user_id)` - returns the channel ID of the direct message with the user with ID `user_id`, or `None` if the ID is invalid.
* `self.get_user_info_by_id(user_id)` - returns a [metadata dictionary](https://api.slack.com/types/user) about the user with ID `user_id`.
* `self.get_user_is_bot(user_id)` - returns `True` if the user with ID `user_id` is a bot user, `False` otherwise.
* `self.text_to_sendable_text(text)` - returns `text`, a plain text string, converted into sendable text.
* `self.sendable_text_to_text(sendable_text)` - returns `sendable_text`, a sendable text string, converted into plain text.
    * The transformation can lose some information for escape sequences, such as link labels.
* `self.get_bot_user_id()` - returns the user ID of the current `SlackBot` instance's Slack account.

Files Overview
--------------

### `src/botty.py`

The entry point for Botty. Implements plugin loading and handling on top of the Slack bot functionality implemented in `src/bot.py`, as well as a few utility functions that are useful for developing plugins.

`example-start-botty.sh` is a Bash script that shows a sample usage of `src/botty.py`. If you edit the script to replace `SLACK_API_TOKEN_GOES_HERE` with an actual API token, you can start Botty simply by running it.

    $ python3 src/botty.py --help
    Usage: ./botty.py --help
        Show this help message
    Usage: ./botty.py
        Start the Botty chatbot for Slack in testing mode with a console chat interface
    Usage: ./botty.py SLACK_BOT_TOKEN
        Start the Botty chatbot for the Slack chat associated with SLACK_BOT_TOKEN, and enter the in-process Python REPL
        SLACK_BOT_TOKEN is a Slack API token (can be obtained from https://api.slack.com/)

### `src/bot.py`

Implements Slack bot functionality, such as receiving/sending messages, managing the connection to the Slack Realtime Messaging API, looking up users/channels, parsing message formatting/escape sequences, and more. This is encapsulated in the `SlackBot` class, which is intended to be extended to make custom Slack bots.

Also implements a mock Slack bot in the `SlackDebugBot` class, which exposes the same interface as `SlackBot`, but all functionality acts on a simulated Slack chat in the terminal. Replacing `SlackBot` with `SlackDebugBot` allows testing and local development without using the real Slack API at all.

### `src/plugins/*`

Folder in which plugins reside. Each plugin is an importable Python module - a `*.py` file, or a folder containing `__init__.py` as a direct child.

The plugins are imported and registered in `src/botty.py`.

Botty ships with several default plugins. For more information about what they do and how they work, look at their docstrings and source code.

For general information about writing plugins, see the "Writing Plugins" section.

### `utils/download-history.py`

`utils/download-history.py` is a standalone utility that downloads history from all channels in the Slack team associated with a given API token.

If previously downloaded history is present, the new history will be transparently appended to the old history.

    $ python3 src/download-history.py
    Usage: download-history.py SLACK_API_TOKEN [SAVE_FOLDER]
        SLACK_API_TOKEN    Slack API token (obtainable from https://api.slack.com/tokens)
        SAVE_FOLDER        Folder to save messages in (defaults to ./@history)

`example-download-history.sh` is a Bash script that shows a sample usage of this utility. If you edit the script to replace `SLACK_API_TOKEN_GOES_HERE` with an actual Slack API token, you can download history simply by running it.

### `utils/process-history.py`

`utils/process-history.py` is a standalone utility that processes and shows history in-memory. With a variety of filtering options, it is very useful for searching through and filtering messages.

    $ python3 src/process-history.py --help
    usage: process-history.py [-h] [--history HISTORY] [-f FILTER_FROM]
                              [-t FILTER_TO] [-c FILTER_CHANNEL] [-u FILTER_USER]
                              [-i FILTER_TEXT] [-s {time,channel,user,text}]
                              [-r CONTEXT]
    
    Slice and filter Slack chat history.
    
    optional arguments:
      -h, --help            show this help message and exit
      --history HISTORY     Directory to look for JSON chat history files in
                            (e.g., "~/.slack-history").
      -f FILTER_FROM, --filter-from FILTER_FROM
                            Show only messages at or after a date/time (e.g., "4pm
                            september 8 2015").
      -t FILTER_TO, --filter-to FILTER_TO
                            Show only messages before or at a date/time (e.g.,
                            "8pm september 9 2015").
      -c FILTER_CHANNEL, --filter-channel FILTER_CHANNEL
                            Show only messages within channels with names matching
                            a specific regular expression (e.g., "general",
                            "general|random").
      -u FILTER_USER, --filter-user FILTER_USER
                            Show only messages by users with usernames or real
                            names matching a specific regular expression (e.g.,
                            "anthony", "[AO]nthon[yo] Zh[ao]ng").
      -i FILTER_TEXT, --filter-text FILTER_TEXT
                            Show only messages with text matching a specified
                            regular expression (e.g., "wings?",
                            "chicken\s+nuggets").
      -s {time,channel,user,text}, --sort {time,channel,user,text}
                            Sort the resulting messages by the specified criteria.
      -r CONTEXT, --context CONTEXT
                            Show a specified number of surrounding messages around
                            the channel in each matched message.

`example-process-history.sh` is a Bash script that shows a sample usage of this utility, filtering out messages in the channel `#general` that include the phrase "wing night" or "nuggets", sorted alphabetically by username.

### `utils/export-history-to-db.py`

`utils/export-history-to-db.py` is a standalone utility that, when run, exports an entire history directory (downloaded using something like `utils/download-history.py`) to a single Sqlite3 database, defaulting to `history.db` in the same directory as the script.