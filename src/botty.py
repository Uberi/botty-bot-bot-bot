#!/usr/bin/env python3

import sys, logging
from collections import deque

from bot import SlackBot

# process settings
#logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logging.basicConfig(filename="botty.log", level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

def initialize_plugins(botty):
    """Import, register, and initialize Botty plugins. Edit the body of this function to change which plugins are loaded."""
    from plugins.arithmetic import ArithmeticPlugin; botty.register_plugin(ArithmeticPlugin(botty))
    from plugins.timezones import TimezonesPlugin; botty.register_plugin(TimezonesPlugin(botty))
    from plugins.poll import PollPlugin; botty.register_plugin(PollPlugin(botty))
    from plugins.wiki import WikiPlugin; botty.register_plugin(WikiPlugin(botty))
    from plugins.haiku import HaikuPlugin; botty.register_plugin(HaikuPlugin(botty))
    from plugins.personality import PersonalityPlugin; botty.register_plugin(PersonalityPlugin(botty))
    from plugins.events import EventsPlugin; botty.register_plugin(EventsPlugin(botty))
    from plugins.now_i_am_dude import NowIAmDudePlugin; botty.register_plugin(NowIAmDudePlugin(botty))
    from plugins.generate_text import GenerateTextPlugin; botty.register_plugin(GenerateTextPlugin(botty))
    from plugins.big_text import BigTextPlugin; botty.register_plugin(BigTextPlugin(botty))
    from plugins.uw_courses import UWCoursesPlugin; botty.register_plugin(UWCoursesPlugin(botty))
    from plugins.spaaace import SpaaacePlugin; botty.register_plugin(SpaaacePlugin(botty))
    from plugins.agario import AgarioPlugin; botty.register_plugin(AgarioPlugin(botty))
    from plugins.snek import SnekPlugin; botty.register_plugin(SnekPlugin(botty))

if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] in {"--help", "-h", "-?"}):
    print("Usage: {} --help".format(sys.argv[0]))
    print("    Show this help message")
    print("Usage: {}".format(sys.argv[0]))
    print("    Start the Botty chatbot for Slack in testing mode with a console chat interface")
    print("Usage: {} SLACK_BOT_TOKEN".format(sys.argv[0]))
    print("    Start the Botty chatbot for the Slack chat associated with SLACK_BOT_TOKEN, and enter the in-process Python REPL")
    print("    SLACK_BOT_TOKEN is a Slack API token (can be obtained from https://api.slack.com/)")
    sys.exit(1)

DEBUG = len(sys.argv) < 2
if DEBUG:
    from bot import SlackDebugBot as SlackBot
    SLACK_TOKEN = ""
    print("No Slack API token specified in command line arguments; starting in local debug mode...")
    print()
else:
    SLACK_TOKEN = sys.argv[1]

class Botty(SlackBot):
    def __init__(self, token):
        super().__init__(token)
        self.plugins = []
        self.last_message_timestamp = None
        self.last_message_thread_id = None
        self.last_message_channel_id = None
        self.recent_events = deque(maxlen=2000) # store the last 2000 events

    def register_plugin(self, plugin_instance):
        self.plugins.append(plugin_instance)

    def on_step(self):
        for plugin in self.plugins:
            if plugin.on_step(): break

    def on_message(self, message_dict):
        self.logger.debug("received message {}".format(message_dict))

        # check if the user is a bot and ignore the message if they are
        user_id = message_dict.get("user", message_dict.get("message", {}).get("user"))
        if isinstance(user_id, str) and self.get_user_is_bot(user_id): return

        message = IncomingMessage(message_dict, is_bot_message=False)
        #try:
        if True:
            # we need to set all of these in one statement because if any of the accessors fail, none of the variables should be updated
            self.last_message_timestamp, self.last_message_thread_id, self.last_message_channel_id = message.timestamp, message.thread_id, message.channel_id
        #except ValueError: pass

        # save recent message events
        if message.is_action_message: self.recent_events.append(message)

        for plugin in self.plugins:
            if plugin.on_message(message):
                self.logger.info("message handled by {}: {}".format(plugin.__class__.__name__, message))
                break

    def respond(self, sendable_text, *, as_thread=True):
        """Say `sendable_text` in the channel/thread that most recently received a message, returning the message ID (unique within each `SlackBot` instance). If `as_thread` is truthy, this will create a thread for the message being responsed to if it wasn't in a thread."""
        assert self.last_message_channel_id is not None, "No message to respond to"
        thread_id = self.last_message_thread_id or (self.last_message_timestamp if as_thread else None)
        return self.say(sendable_text, channel_id=self.last_message_channel_id, thread_id=thread_id)

    def respond_complete(self, sendable_text, *, as_thread=True):
        """Say `sendable_text` in the channel (and thread, if applicable) that most recently received a message, waiting until the message is successfully sent, returning the message timestamp. If `as_thread` is truthy, this will create a thread for the message being responsed to if it wasn't in a thread."""
        assert self.last_message_channel_id is not None, "No message to respond to"
        thread_id = self.last_message_thread_id or (self.last_message_timestamp if as_thread else None)
        return self.say_complete(sendable_text, channel_id=self.last_message_channel_id, thread_id=self.last_message_thread_id)

    def reply(self, emoticon):
        """React with `emoticon` to the most recently received message."""
        assert self.last_message_channel_id is not None and self.last_message_timestamp is not None, "No message to reply to"
        return self.react(self.last_message_channel_id, self.last_message_timestamp, emoticon)

    def unreply(self, emoticon):
        """Remove `emoticon` reaction from the most recently received message."""
        assert self.last_message_channel_id is not None and self.last_message_timestamp is not None, "No message to unreply to"
        return self.unreact(self.last_message_channel_id, self.last_message_timestamp, emoticon)

class IncomingMessage:
    """Represents a single incoming message event."""
    def __init__(self, message_dict, is_bot_message):
        self.message_dict = message_dict
        self.is_bot_message = is_bot_message

    def __repr__(self): return "<Message {}>".format(self.message_dict)

    def __iter__(self): return iter(self.message_dict)

    @property
    def is_action_message(self):
        """Returns `True` if the message represents an action by a user, as opposed to things we usually don't consider user actions, like server pings or going offline, `False` otherwise."""
        return self.message_dict.get("type") not in {"ping", "pong", "presence_change", "user_typing", "reconnect_url"}

    @property
    def is_text_message(self):
        """Returns `True` if the message represents a text message, `False` otherwise. If this returns `True`, the `Message.timestamp`, `Message.text`, `Message.user_id`, and `Message.channel_id` methods will be available."""
        if self.message_dict.get("type") != "message": return False
        if not isinstance(self.message_dict.get("ts"), str): return False
        if not isinstance(self.message_dict.get("channel"), str): return False
        if isinstance(self.message_dict.get("text"), str) and isinstance(self.message_dict.get("user"), str):
            return True # ordinary message
        if (
            self.message_dict.get("subtype") == "message_changed" and
            isinstance(self.message_dict.get("message"), dict) and
            isinstance(self.message_dict["message"].get("user"), str) and
            isinstance(self.message_dict["message"].get("channel"), str) and
            isinstance(self.message_dict["message"].get("text"), str)
        ):
            return True # edited message
        return False # not a text message

    @property
    def is_user_message(self):
        """Returns `True` if the message represents a message sent by a real user (i.e., not a bot), `False` otherwise."""
        return not self.is_bot_message

    @property
    def is_user_text_message(self):
        """Returns `True` if the message represents a text message sent by a real user (i.e., not a bot), `False` otherwise."""
        return not self.is_bot_message and self.is_text_message

    @property
    def is_reaction_addition(self):
        """Returns `True` if the message represents a reaction being added, `False` otherwise."""
        return self.message_dict.get("type") == "reaction_added" and self.channel_id and self.user_id

    @property
    def is_reaction_removal(self):
        """Returns `True` if the message represents a reaction being removed, `False` otherwise."""
        return self.message_dict.get("type") == "reaction_removed" and self.channel_id and self.user_id

    @property
    def timestamp(self):
        """Returns the timestamp of the message, or raises a `ValueError` if there is none."""
        reaction_timestamp = self.message_dict.get("item", {}).get("ts")
        timestamp = self.message_dict.get("ts", reaction_timestamp)
        if not isinstance(timestamp, str): raise ValueError("Message timestamp should be a string, but is \"{}\" instead".format(repr(timestamp)))
        return timestamp

    @property
    def text(self):
        """Returns the text content of the message as a string, or raises a `ValueError` if there is none."""
        submessage_text = self.message_dict.get("message", {}).get("text")
        text = self.message_dict.get("text", submessage_text)
        if not isinstance(text, str): raise ValueError("Message text should be a string, but is \"{}\" instead".format(repr(text)))
        return text

    @property
    def user_id(self):
        """Returns the ID of the user that sent the message, or raises a `ValueError` if there is none."""
        submessage_channel = self.message_dict.get("message", {}).get("user")
        user_id = self.message_dict.get("user", submessage_channel)
        if not isinstance(user_id, str): raise ValueError("Message user ID should be a string, but is \"{}\" instead".format(repr(user_id)))
        return user_id

    @property
    def channel_id(self):
        """Returns the ID of the channel that the message is in, or raises a `ValueError` if there is none."""
        reaction_channel = self.message_dict.get("item", {}).get("channel")
        submessage_channel = self.message_dict.get("message", {}).get("channel", reaction_channel)
        channel_id = self.message_dict.get("channel", submessage_channel)
        if not isinstance(channel_id, str): raise ValueError("Message channel ID should be a string, but is \"{}\" instead".format(repr(channel_id)))
        return channel_id

    @property
    def thread_id(self):
        """Returns the ID of the thread that the message is in, or `None` if the message is not in a thread."""
        submessage_thread = self.message_dict.get("message", {}).get("thread_ts")
        thread_id = self.message_dict.get("thread_ts", submessage_thread)
        if thread_id is not None and not isinstance(thread_id, str): raise ValueError("Message thread ID should be a string, but is \"{}\" instead".format(repr(thread_id)))
        return thread_id

    @property
    def reaction(self):
        """Returns the name of the reaction for the reaction addition/removal message, or raises a `ValueError` if there is none."""
        reaction = self.message_dict.get("reaction")
        if not isinstance(reaction, str): raise ValueError("Message reaction value should be a string, but is \"{}\" instead".format(repr(reaction)))
        return reaction

botty = Botty(SLACK_TOKEN)
initialize_plugins(botty)

# start administrator console in production mode
if not DEBUG:
    def say(channel, text):
        """Say `text` in `channel` where `text` is a sendable text string and `channel` is a channel name like #general."""
        botty.say(text, channel_id=botty.get_channel_id_by_name(channel))

    def reload_plugin(package_name, class_name):
        """Reload plugin from its plugin class `class_name` from package `package_name`."""
        # obtain the new plugin
        import importlib
        plugin_module = importlib.import_module(package_name) # this will not re-initialize the module, since it's been previously imported
        importlib.reload(plugin_module) # re-initialize the module
        PluginClass = getattr(plugin_module, class_name)

        # replace the old plugin with the new one
        for i, plugin in enumerate(botty.plugins):
            if isinstance(plugin, PluginClass):
                del botty.plugins[i]
                break
        botty.register_plugin(PluginClass(botty))

    def sane():
        """Force the administrator's console into a reasonable default - useful for recovering from weird terminal states."""
        import os
        os.system("stty sane")

    from datetime import datetime
    from plugins.utilities import BasePlugin
    def on_message_default(plugin, message): return False
    def on_message_disabled(plugin, message): return True
    def on_message_print(plugin, message):
        """Print out all incoming events - useful for interactive RTM API debugging."""
        if message.get("type") == "message":
            timestamp = datetime.fromtimestamp(int(message["ts"].split(".")[0]))
            channel_name = botty.get_channel_name_by_id(message.get("channel", message.get("previous_message", {}).get("channel")))
            user_name = botty.get_user_name_by_id(message.get("user", message.get("previous_message", {}).get("user")))
            text = message.get("text", message.get("previous_message", {}).get("text"))
            new_text = message.get("message", {}).get("text")
            if new_text:
                print("{timestamp} #{channel} | @{user} {subtype}: {text} -> {new_text}".format(
                    timestamp=timestamp, channel=channel_name, user=user_name,
                    subtype=message.get("subtype", "message"), text=text, new_text=new_text
                ))
            else:
                print("{timestamp} #{channel} | @{user} {subtype}: {text}".format(
                    timestamp=timestamp, channel=channel_name, user=user_name,
                    subtype=message.get("subtype", "message"), text=text
                ))
        elif message.get("type") not in {"ping", "pong", "presence_change", "user_typing", "reconnect_url"}:
            print(message)
        return False
    on_message = on_message_default
    class AdHocPlugin(BasePlugin):
        def __init__(self, bot): super().__init__(bot)
        def on_message(self, message): return on_message(self, message)
    if not any(isinstance(plugin, AdHocPlugin) for plugin in botty.plugins): # plugin hasn't already been added
        botty.plugins.insert(0, AdHocPlugin(botty)) # the plugin should go before everything else to be able to influence every message

    botty.administrator_console(globals())

botty.start_loop()
