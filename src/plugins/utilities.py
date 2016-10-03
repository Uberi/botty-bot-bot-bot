#!/usr/bin/env python3

"""
Utilities and classes for Botty plugins.

Should be imported by all Botty plugins.
"""

import os, re

CHAT_HISTORY_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "@history")

class BasePlugin:
    """Base class for Botty plugins. Should be imported from plugins using `from .utilities import BasePlugin`."""
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

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

    def untag_word(self, word):
        """Returns `word` where characters are modified to appear the same but not tag users."""
        homoglyph_replacements = [
            # basically identical replacements
            (",", "\u201A"), ("-", "\u2010"), (";", "\u037E"), ("A", "\u0391"), ("B", "\u0392"),
            ("C", "\u0421"), ("D", "\u216E"), ("E", "\u0395"), ("H", "\u0397"), ("I", "\u0399"),
            ("J", "\u0408"), ("K", "\u039A"), ("L", "\u216C"), ("M", "\u039C"), ("N", "\u039D"),
            ("O", "\u039F"), ("P", "\u03A1"), ("S", "\u0405"), ("T", "\u03A4"), ("V", "\u2164"),
            ("X", "\u03A7"), ("Y", "\u03A5"), ("Z", "\u0396"), ("a", "\u0430"), ("c", "\u03F2"),
            ("d", "\u217E"), ("e", "\u0435"), ("i", "\u0456"), ("j", "\u0458"), ("l", "\u217C"),
            ("m", "\u217F"), ("o", "\u03BF"), ("p", "\u0440"), ("s", "\u0455"), ("v", "\u03BD"),
            ("x", "\u0445"), ("y", "\u0443"), ("\u00DF", "\u03B2"), ("\u00E4", "\u04D3"), ("\u00F6", "\u04E7"),
            
            # similar replacements
            ("/", "\u2044"), ("F", "\u03DC"), ("G", "\u050C"), ("\u00C4", "\u04D2"), ("\u00D6", "\u04E6"),
            
            # fixed width replacements
            ("*", "\uFF0A"), ("!", "\uFF01"), ("\"", "\uFF02"), ("#", "\uFF03"), ("$", "\uFF04"),
            ("%", "\uFF05"), ("&", "\uFF06"), ("'", "\uFF07"), ("(", "\uFF08"), (")", "\uFF09"),
            ("+", "\uFF0B"), (".", "\uFF0E"), ("0", "\uFF10"), ("1", "\uFF11"), ("2", "\uFF12"),
            ("3", "\uFF13"), ("4", "\uFF14"), ("5", "\uFF15"), ("6", "\uFF16"), ("7", "\uFF17"),
            ("8", "\uFF18"), ("9", "\uFF19"), (":", "\uFF1A"), ("<", "\uFF1C"), ("=", "\uFF1D"),
            (">", "\uFF1E"), ("?", "\uFF1F"), ("@", "\uFF20"), ("Q", "\uFF31"), ("R", "\uFF32"),
            ("U", "\uFF35"), ("W", "\uFF37"), ("[", "\uFF3B"), ("\\", "\uFF3C"), ("]", "\uFF3D"),
            ("^", "\uFF3E"), ("_", "\uFF3F"), ("`", "\uFF40"), ("b", "\uFF42"), ("f", "\uFF46"),
            ("g", "\uFF47"), ("h", "\uFF48"), ("k", "\uFF4B"), ("n", "\uFF4E"), ("q", "\uFF51"),
            ("r", "\uFF52"), ("t", "\uFF54"), ("u", "\uFF55"), ("w", "\uFF57"), ("z", "\uFF5A"),
            ("{", "\uFF5B"), ("|", "\uFF5C"), ("}", "\uFF5D"), ("~", "\uFF5E"),
        ]
        
        for character, homoglyph in homoglyph_replacements:
            new_word = word.replace(character, homoglyph, 1)
            if new_word != word:
                return new_word
        return word

    def on_step(self): return False
    def on_message(self, message): return False

    def get_message_text(self, message): return self.bot.get_message_text(message)
    def get_message_timestamp(self, message): return self.bot.get_message_timestamp(message)
    def get_message_channel(self, message): return self.bot.get_message_channel(message)
    def get_message_sender(self, message): return self.bot.get_message_sender(message)
    def say(self, channel_id, sendable_text): return self.bot.say(channel_id, sendable_text)
    def say_raw(self, channel_id, text): return self.bot.say(channel_id, self.text_to_sendable_text(text))
    def say_complete(self, channel_id, sendable_text): return self.bot.say_complete(channel_id, sendable_text)
    def say_raw_complete(self, channel_id, text): return self.bot.say_complete(channel_id, self.text_to_sendable_text(text))
    def respond(self, text): return self.bot.respond(text)
    def respond_raw(self, text): return self.bot.respond(self.text_to_sendable_text(text))
    def respond_complete(self, text): return self.bot.respond_complete(text)
    def respond_raw_complete(self, text): return self.bot.respond_complete(self.text_to_sendable_text(text))
    def react(self, channel_id, timestamp, emoticon): return self.bot.react(channel_id, timestamp, emoticon)
    def unreact(self, channel_id, timestamp, emoticon): return self.bot.unreact(channel_id, timestamp, emoticon)
    def reply(self, emoticon): return self.bot.reply(emoticon)
    def unreply(self, emoticon): return self.bot.unreply(emoticon)
    def get_channel_name_by_id(self, channel_id): return self.bot.get_channel_name_by_id(channel_id)
    def get_channel_id_by_name(self, channel_name): return self.bot.get_channel_id_by_name(channel_name)
    def get_user_id_by_name(self, user_name): return self.bot.get_user_id_by_name(user_name)
    def get_user_name_by_id(self, user_id): return self.bot.get_user_name_by_id(user_id)
    def get_direct_message_channel_id_by_user_id(self, user_id): return self.bot.get_direct_message_channel_id_by_user_id(user_id)
    def get_user_info_by_id(self, user_id): return self.bot.get_user_info_by_id(user_id)
    def text_to_sendable_text(self, text): return self.bot.text_to_sendable_text(text)
    def sendable_text_to_text(self, sendable_text): return self.bot.sendable_text_to_text(sendable_text)
    def get_bot_user_id(self): return self.bot.bot_user_id
