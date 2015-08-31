#!/usr/bin/env python3

import os

CHAT_HISTORY_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "@history")

class BasePlugin:
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

    def get_text_message_body(self, message):
        """Returns the text value of `message` if it is a valid text message, or `None` otherwise"""
        if message.get("type") != "message": return None
        if not isinstance(message.get("user"), str): return None
        if not isinstance(message.get("text"), str): return None
        if not isinstance(message.get("ts"), str): return None
        return message["text"]

    def get_history_files(self):
        """Returns a mapping from channel names to absolute file paths of their history entries"""
        for dirpath, _, filenames in os.walk(CHAT_HISTORY_DIRECTORY):
            result = {}
            for history_file in filenames:
                channel_name, extension = os.path.splitext(os.path.basename(history_file))
                if extension != ".json": continue
                result["#" + channel_name] = os.path.join(dirpath, history_file)
            return result
        return {}

    def on_step(self): return False
    def on_message(self, message): return False

    def say(self, channel_id, text): self.bot.say(channel_id, text)
    def respond(self, text): self.bot.respond(text)
    def get_channel_name_by_id(self, channel_id): return self.bot.get_channel_name_by_id(channel_id)
    def get_channel_id_by_name(self, channel_name): return self.bot.get_channel_id_by_name(channel_name)
    def get_user_id_by_name(self, user_name): return self.bot.get_user_id_by_name(user_name)
    def get_user_name_by_id(self, user_id): return self.bot.get_user_name_by_id(user_id)
