Botty Bot Bot Bot
=================
Personable chatbot for [Slack](https://slack.com/) using the [Slack Realtime Messaging API](https://api.slack.com/rtm).

Features
--------

* **Test mode with simulated chat** in the command line: test Botty and Botty plugins offline, without using Slack at all.
* In-process **Python REPL**: monitor, patch, or control running Botty instances **without restarting** or editing files.
* Simple and reliable: Botty gracefully handles **plugin exceptions**, **network issues**, and more. Instances have been left continuously running for the past few months without needing any maintenance.
* Robust **plugin API**: friendly error messages and well-documented functions makes development fast and productive - each plugin is simply a Python class.
* Excellent **Slack protocol compliance**: supports periodic ping, message escape sequences, and more, on top of the official Slack Python library.

Writing Plugins
---------------

### Overview

Botty plugins are simply Python classes. By convention, we organize these onto one class per file, and put these files under the `src/plugins` directory. There's an example in the "Types of Text" section below.

Plugin classes should inherit from `BasePlugin` (from `src/plugins/utilities.py`).

Plugin classes can optionally implement the `on_step()` method, which is called on every time step (except in the situation described below) - generally several times a second. For multiple plugins, the `on_step` methods are called in the order that the plugins are registered.

If an plugin's `on_step` method returns a truthy value, all plugins after it will not have their `on_step` method called for that time step - returning a truthy value stops step processing for the current time step.

Plugin classes can optionally implement the `on_message(message)` method, which is called upon receiving a message (except in the situation described below). For multiple plugins, the `on_message` methods are called in the order that the plugins are registered, and always after `on_step` methods have been called.

The `message` in `on_message(message)` is a JSON dictionary representing a Slack event. The format of this dictionary is documented in the [Slack API documentation](https://api.slack.com/rtm), under the "Events" section. Generally, we only care about the [message event](https://api.slack.com/events/message).

However, it is a good idea to avoid accessing fields of the JSON dictionary directly if possible; if these change in the future, your code could break. If you just need the text, channel, or sender, use the `self.get_message_text`, `self.get_message_channel`, and `self.get_message_sender` methods instead.

If an plugin's `on_message` method returns a truthy value, all plugins after it will not have their `on_message` method called for that message - returning a truthy value stops message processing for the current message, representing that the message has been fully handled.

### API

Plugins inherit a number of methods from the `BasePlugin` class:

* `self.get_message_text(message)` - returns the text value of `message` if it is a valid text message, or `None` otherwise.
* `self.get_message_channel(message)` - returns the ID of the channel containing `message` if there is one, or `None` otherwise.
* `self.get_message_sender(message)` - returns the ID of the user who sent `message` if there is one, or `None` otherwise.
* `self.say(channel_id, sendable_text)` - send a message containing `sendable_text` to the channel with ID `channel_id`.
    * `sendable_text` must be sendable text (see "Types of Text" for details).
    * Plain text can be converted into sendable text using `self.text_to_sendable_text`.
* `self.say_raw(channel_id, text)` - send a message containing `text` to the channel with ID `channel_id`.
    * Does the same thing as `self.say`, but `text` is plain text instead of sendable text.
* `self.respond(text)` - does the same thing as `self.say`, but always sends the message to the channel of the message we most recently processed.
    * If this is called within an `on_message(message)` handler, the message will always be sent to the same channel as the one containing `message`.
* `self.respond_raw(text)` - does the same thing as `self.respond`, but `text` is plain text instead of sendable text.
* `self.get_channel_name_by_id(channel_id)` - returns the name of the channel with ID `channel_id`, or `None` if the ID is invalid.
    * Channels include public channels, direct messages with other users, and private groups.
* `self.get_channel_id_by_name(channel_name)` - returns the ID of the channel with name `channel_name`, or `None` if there is no such channel.
    * Channels include public channels, direct messages with other users, and private groups.
* `self.get_user_name_by_id(user_id)` - returns the username of the user with ID `user_id`.
* `self.get_user_id_by_name(user_id)` - returns the ID of the user with username `user_name`, or `None` if the ID is invalid.
* `self.get_direct_message_channel_id_by_user_id(user_id)` - returns the channel ID of the direct message with the user with ID `user_id`, or `None` if the ID is invalid.
* `self.text_to_sendable_text(text)` - returns `text`, a plain text string, converted into sendable text.
* `self.sendable_text_to_text(sendable_text)` - returns `sendable_text`, a sendable text string, converted into plain text.
    * The transformation can lose some information for escape sequences, such as link labels.

Plugins are registered in `src/botty.py`. Suppose you have a plugin called `TestPlugin` (in other words, a class called `TestPlugin`) in `src/plugins/test.py`. Then, in `src/botty.py`, you would add the following with the other plugin imports:

```python
from plugins.test import TestPlugin
botty.register_plugin(TestPlugin(botty))
```

### Types of Text

There are actually three different formats for text in Slack messages:

* **Sendable format** is the format of text that is suitable for sending as the body of messages in the Slack API, such as for message contents.
    * **Sendable text** is text that follows the sendable format.
    * Sendable text should generally be considered opaque, since you generally won't want to go through the effort of dealing with the syntax.
    * The main difference between sendable text and server text is that sendable text has bare links, while server text surrounds links with `<` and `>`.
    * That means that if you send server text instead of sendable text, links will have angle brackets around them.
* **Plain format** is the lack of any fixed format.
    * **Plain text** is text that has no fixed format - it can contain anything.
    * The main difference between plain text and sendable text is that sendable text has the `<`, `>`, and `&` characters HTML-escaped, while plain text does not.
* **Server format** is the format of text received from the Slack API, such as for message contents.
    * **Server text** is text that follows server format.
    * Plugins generally don't have to care about server text because functions in the plugin API that deal with text will return either sendable or plain text.

Sendable text should be used for sending parts of Slack messages that we receive, and plain text should be used for everything else. This is because **sendable text can represent more information than plain text can**, such as channel/user references, links, and more. Therefore, **converting sendable text to plain text will lose this extra information**.

However, **sendable text has special formatting that needs to be explicitly handled in code**. For things like sending the text to a search engine as a query, it is better to send the plain text version, since it will not have any of the special formatting.

Suppose we have a plugin that attempts to evaluate all messages as Python code and responds with the results:

```python
from .utilities import BasePlugin
class ArithmeticPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, message):
        sendable_text = self.get_message_text(message)
        if sendable_text is None: return False
        text = self.sendable_text_to_text(sendable_text) # convert sendable text to plain text

        try: result = str(eval(text)) # we evaluate the plain text `text` rather than the sendable text `sendable_text`
        except Exception as e: result = str(e)
        sendable_result = self.text_to_sendable_text(result)

        # we send `sendable_text` instead of `text` to preserve sendable formatting that is lost when converting sendable text to plain text
        self.respond("{} :point_right: {}".format(sendable_text, sendable_result))
        return True
```

Deployment
----------

To set up the prerequisites on a Debian-based Linux distribution, run `./setup.sh`.

To test locally, run `python3 src/botty.py` in the terminal. After Botty starts, there will be a command line simulated chat interface for testing purposes.

To run in production mode, run `python3 src/botty.py SLACK_API_TOKEN_GOES_HERE`, where `SLACK_API_TOKEN_GOES_HERE` is the Slack API token (obtainable from the [Slack API site](https://api.slack.com/)). Alternatively, edit `example-start-botty.sh` to replace `SLACK_API_TOKEN_GOES_HERE` with the Slack API token, then run `./example-start-botty.sh`.

Currently, a Botty instance is deployed for [nokappa.slack.com](https://nokappa.slack.com/) on DigitalOcean inside a [tmux](https://tmux.github.io/) session, to allow monitoring and management over SSH. Code updates are done via Git.

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

### `src/download-history.py`

`src/download-history.py` is a standalone utility that downloads history from all channels in the Slack team associated with a given API token.

If previously downloaded history is present, the new history will be transparently appended to the old history.

    $ python3 src/download-history.py
    Usage: download-history.py SLACK_API_TOKEN [SAVE_FOLDER]
        SLACK_API_TOKEN    Slack API token (obtainable from https://api.slack.com/tokens)
        SAVE_FOLDER        Folder to save messages in (defaults to ./@history)

`example-download-history.sh` is a Bash script that shows a sample usage of this utility. If you edit the script to replace `SLACK_API_TOKEN_GOES_HERE` with an actual Slack API token, you can download history simply by running it.

License
-------

Copyright 2015 `Anthony Zhang (Uberi) <https://uberi.github.io>`__.

The source code is available online at `GitHub <https://github.com/Uberi/botty-bot-bot-bot>`__.

This program is made available under the MIT license. See ``LICENSE.txt`` in the project's root directory for more information.
