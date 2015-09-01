#!/usr/bin/env python3

import sys
import logging

#wip: interactive admin console running in a background thread

from bot import SlackBot
from plugins.arithmetic import ArithmeticPlugin
from plugins.poll import PollPlugin
from plugins.reminders import RemindersPlugin
from plugins.wiki import WikiPlugin
from plugins.generate_text import GenerateTextPlugin
from plugins.haiku import HaikuPlugin
from plugins.personality import PersonalityPlugin
from plugins.big_text import BigTextPlugin

LOG_LEVEL = logging.INFO

if __name__ == "__main__":
    if len(sys.argv) > 2:
        print("Usage: {} [SLACK_BOT_TOKEN]".format(sys.argv[0]))
        print("    Start the Botty chatbot for Slack.")
        print("    SLACK_BOT_TOKEN is a Slack API token, which can be obtained from https://api.slack.com/.")
        print("    If SLACK_BOT_TOKEN is omitted, Botty starts in debug mode with a console interface for testing purposes.")
        print("    Otherwise, Botty connects to the Slack chat associated with SLACK_BOT_TOKEN.")
        sys.exit(1)

    logging.basicConfig(stream=sys.stdout, level=LOG_LEVEL, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    if len(sys.argv) < 2: # no Slack token specified, use debug mode
        from bot import SlackDebugBot as SlackBot
        SLACK_TOKEN = ""
    else:
        SLACK_TOKEN = sys.argv[1]

class Botty(SlackBot):
    def __init__(self, token):
        super().__init__(token)
        self.plugins = []
        self.last_message_channel_id = None

    def register_plugin(self, plugin_instance):
        self.plugins.append(plugin_instance)

    def on_step(self):
        for plugin in self.plugins:
            if plugin.on_step(): break

    def on_message(self, message):
        self.logger.debug("received message message {}".format(message))
        if isinstance(message.get("channel"), str): # store the channel ID so responding can work
            self.last_message_channel_id = message["channel"]
        for plugin in self.plugins:
            if plugin.on_message(message):
                self.logger.info("message handled by {}: {}".format(plugin.__class__.__name__, message))
                break

    def respond(self, text):
        """Say `text` in the channel that most recently received a message."""
        assert self.last_message_channel_id is not None, "No message to respond to"
        self.say(self.last_message_channel_id, text)

if __name__ == "__main__":
    botty = Botty(SLACK_TOKEN)

    # register plugins
    botty.register_plugin(ArithmeticPlugin(botty))
    botty.register_plugin(PollPlugin(botty))
    botty.register_plugin(RemindersPlugin(botty))
    botty.register_plugin(WikiPlugin(botty))
    botty.register_plugin(HaikuPlugin(botty))
    botty.register_plugin(PersonalityPlugin(botty))
    botty.register_plugin(GenerateTextPlugin(botty))
    botty.register_plugin(BigTextPlugin(botty))

    botty.start_loop()
