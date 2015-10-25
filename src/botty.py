#!/usr/bin/env python3

import sys, logging

from bot import SlackBot

if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] in {"--help", "-h", "-?"}):
    print("Usage: {} --help".format(sys.argv[0]))
    print("    Show this help message")
    print("Usage: {}".format(sys.argv[0]))
    print("    Start the Botty chatbot for Slack in testing mode with a console chat interface")
    print("Usage: {} SLACK_BOT_TOKEN".format(sys.argv[0]))
    print("    Start the Botty chatbot for the Slack chat associated with SLACK_BOT_TOKEN, and enter the in-process Python REPL")
    print("    SLACK_BOT_TOKEN is a Slack API token (can be obtained from https://api.slack.com/)")
    sys.exit(1)

# process settings
#logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.basicConfig(filename="botty.log", level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
DEBUG = len(sys.argv) < 2
if DEBUG:
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

botty = Botty(SLACK_TOKEN)

from plugins.arithmetic import ArithmeticPlugin
botty.register_plugin(ArithmeticPlugin(botty))

from plugins.poll import PollPlugin
botty.register_plugin(PollPlugin(botty))

from plugins.reminders import RemindersPlugin
botty.register_plugin(RemindersPlugin(botty))

from plugins.wiki import WikiPlugin
botty.register_plugin(WikiPlugin(botty))

from plugins.haiku import HaikuPlugin
botty.register_plugin(HaikuPlugin(botty))

from plugins.personality import PersonalityPlugin
botty.register_plugin(PersonalityPlugin(botty))

from plugins.events import EventsPlugin
botty.register_plugin(EventsPlugin(botty))

from plugins.generate_text import GenerateTextPlugin
botty.register_plugin(GenerateTextPlugin(botty))

from plugins.big_text import BigTextPlugin
botty.register_plugin(BigTextPlugin(botty))

# start administrator console in production mode
if not DEBUG:
    botty.administrator_console(globals())
    
    # define useful functions for administration
    def say(channel, text):
        """Say `text` in `channel` where `text` is a sendable text string and `channel` is a channel name like #general."""
        botty.say(botty.get_channel_id_by_name(channel), text)
    def reload_plugin(package_name, class_name):
        """Reload plugin from its plugin class `class_name` from package `package_name`."""
        # add the new 
        import importlib
        plugin_module = importlib.import_module(package_name) # this will not re-initialize the module, since it's been previously imported
        importlib.reload(plugin_module) # re-initialize the module
        PluginClass = getattr(plugin_module, class_name)

        # replace the plugin
        for i, plugin in enumerate(botty.plugins):
            if isinstance(plugin, PluginClass):
                del botty.plugins[i]
                break
        botty.register_plugin(PluginClass(botty))

botty.start_loop()
