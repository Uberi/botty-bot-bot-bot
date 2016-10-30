Botty Bot Bot Bot
=================
Personable chatbot for [Slack](https://slack.com/) using the [Slack Realtime Messaging API](https://api.slack.com/rtm).

Features
--------

* **Test mode with simulated chat** in the command line: try Botty and Botty plugins offline, without using Slack at all.
* In-process **Python REPL**: monitor, patch, or control running Botty instances **without restarting** or editing files.
* Simple and reliable: Botty gracefully handles **plugin exceptions**, **network issues**, and more.
* Robust **plugin API**: friendly error messages and well-documented functions makes development fast and productive - each plugin is simply a Python class.
* Excellent **Slack protocol compliance**: supports periodic ping, message escape sequences, and more, on top of the official Slack Python library.

Deployment
----------

To set up the prerequisites on a Debian-based Linux distribution, run `./setup.sh`.

To test locally, run `python3 src/botty.py` in the terminal. After Botty starts, there will be a command line simulated chat interface for testing purposes.

To run in production mode, run `python3 src/botty.py SLACK_API_TOKEN_GOES_HERE`, where `SLACK_API_TOKEN_GOES_HERE` is the Slack API token (obtainable from the [Slack API site](https://api.slack.com/)). Alternatively, edit `example-start-botty.sh` to replace `SLACK_API_TOKEN_GOES_HERE` with the Slack API token, then run `./example-start-botty.sh`.

Currently, a Botty instance is deployed for [nokappa.slack.com](https://nokappa.slack.com/) on DigitalOcean inside a [tmux](https://tmux.github.io/) session, to allow monitoring and management over SSH. Code updates are done via Git.

Developing Botty
----------------

See the "Deployment" section for information about setting up an environment suitable for developing Botty with.

Botty ships with several plugins by default, some of which require API keys or take some time to start. If you don't need those plugins, simply comment out the relevant lines in the body of the `initialize_plugins` function in `src/botty.py` to disable them.

See the [code reference](https://github.com/Uberi/botty-bot-bot-bot/blob/master/docs/reference.md) for API documentation, project file layout, and more.

See the [plugin writing guide](https://github.com/Uberi/botty-bot-bot-bot/blob/master/docs/writing-plugins.md) for information about how to develop your own Botty plugins.

License
-------

Copyright 2015-2016 [Anthony Zhang (Uberi)](https://anthony-zhang.me).

The source code is available online at [GitHub](https://github.com/Uberi/botty-bot-bot-bot).

This program is made available under the MIT license. See ``LICENSE.txt`` in the project's root directory for more information.
