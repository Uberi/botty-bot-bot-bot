#!/usr/bin/env python3

"""
Utilities and classes for Botty plugins.

Should be imported by all Botty plugins.
"""

import os, re
import functools

CHAT_HISTORY_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "@history")

class BasePlugin:
    """Base class for Botty plugins. Should be imported from plugins using `from .utilities import BasePlugin`."""
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger.getChild(self.__class__.__name__)

        self.flows = {}

    def get_history_files(self):
        """Returns a mapping from channel IDs to absolute file paths of their history entries"""
        for dirpath, _, filenames in os.walk(CHAT_HISTORY_DIRECTORY):
            result = {}
            for history_file in filenames:
                channel_id, extension = os.path.splitext(os.path.basename(history_file))
                if extension != ".json": continue
                result[channel_id] = os.path.join(dirpath, history_file)
            return result
        return {}

    def on_step(self): return False
    def on_message(self, message): return False

    def say(self, sendable_text, *, channel_id, thread_id=None):          return self.bot.say(sendable_text, channel_id=channel_id, thread_id=thread_id)
    def say_raw(self, text, *, channel_id, thread_id=None):               return self.bot.say(self.text_to_sendable_text(text), channel_id=channel_id, thread_id=thread_id)
    def say_complete(self, sendable_text, *, channel_id, thread_id=None): return self.bot.say_complete(sendable_text, channel_id=channel_id, thread_id=thread_id)
    def say_raw_complete(self, text, *, channel_id, thread_id=None):      return self.bot.say_complete(self.text_to_sendable_text(text), channel_id=channel_id, thread_id=thread_id)
    def respond(self, sendable_text, *, as_thread=False):                 return self.bot.respond(sendable_text, as_thread=as_thread)
    def respond_raw(self, text, *, as_thread=False):                      return self.bot.respond(self.text_to_sendable_text(text), as_thread=as_thread)
    def respond_complete(self, sendable_text, *, as_thread=False):        return self.bot.respond_complete(sendable_text, as_thread=as_thread)
    def respond_raw_complete(self, text, *, as_thread=False):             return self.bot.respond_complete(self.text_to_sendable_text(text), as_thread=as_thread)
    def react(self, channel_id, timestamp, emoticon):                     return self.bot.react(channel_id, timestamp, emoticon)
    def unreact(self, channel_id, timestamp, emoticon):                   return self.bot.unreact(channel_id, timestamp, emoticon)
    def reply(self, emoticon):                                            return self.bot.reply(emoticon)
    def unreply(self, emoticon):                                          return self.bot.unreply(emoticon)
    def get_channel_name_by_id(self, channel_id):                         return self.bot.get_channel_name_by_id(channel_id)
    def get_channel_id_by_name(self, channel_name):                       return self.bot.get_channel_id_by_name(channel_name)
    def get_user_id_by_name(self, user_name):                             return self.bot.get_user_id_by_name(user_name)
    def get_user_name_by_id(self, user_id):                               return self.bot.get_user_name_by_id(user_id)
    def get_direct_message_channel_id_by_user_id(self, user_id):          return self.bot.get_direct_message_channel_id_by_user_id(user_id)
    def get_user_info_by_id(self, user_id):                               return self.bot.get_user_info_by_id(user_id)
    def get_user_is_bot(self, user_id):                                   return self.bot.get_user_is_bot(user_id)
    def text_to_sendable_text(self, text):                                return self.bot.text_to_sendable_text(text)
    def sendable_text_to_text(self, sendable_text):                       return self.bot.sendable_text_to_text(sendable_text)
    def get_bot_user_id(self):                                            return self.bot.bot_user_id

class Flow:
    """Create a new `Flow` instance (which map keys to generator iterators) with `generator_function` as its generator function. This class can be used to replace many complex message handling state machines with clean and concise Python code."""
    def __init__(self, generator_function):
        self.generator_function = generator_function
        self.generator_iterators = {}

    def start(self, flow_key, parameter_data = None):
        """Discards the current generator iterator associated with key `flow_key`, creates a new state machine from the generator function by calling it with `parameter_data` as an argument, then runs the state machine until it first yields."""
        self.generator_iterators[flow_key] = self.generator_function(parameter_data)
        next(self.generator_iterators[flow_key]) # run the generator all the way up until it first yields

    def is_running(self, flow_key):
        """Returns `True` if there is currently a generator iterator associated with key `flow_key`, `False` otherwise."""
        return flow_key in self.generator_iterators

    def step(self, flow_key, yield_data = None):
        """Returns the result of running the generator iterator associated with key `flow_key` (sending the iterator `yield_data` in the process), or `False` if there is no such generator iterator."""
        if flow_key not in self.generator_iterators: return False
        try:
            return self.generator_iterators[flow_key].send(yield_data)
        except StopIteration as e:
            del self.generator_iterators[flow_key] # remove the completed flow
            return e.value
        return False

def untag_word(word):
    """Returns `word` where characters are modified to appear the same but not tag users."""
    assert isinstance(word, str), "`word` must be a string"
    homoglyph_replacements = [ # glyphs that look similar to the glyphs that can tag users, in descending order by similarity
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

def clockify(dt):
    day_ratio = ((dt.hour % 12) + ((dt.minute + (dt.second / 60)) / 60)) / 12
    clock_emoji = [
        "clock12", "clock1230", "clock1", "clock130", "clock2",
        "clock230", "clock3", "clock330", "clock4", "clock430",
        "clock5", "clock530", "clock6", "clock630", "clock7",
        "clock730", "clock8", "clock830", "clock9", "clock930",
        "clock10", "clock1030", "clock11", "clock1130", "clock12"]
    return clock_emoji[round(day_ratio * (len(clock_emoji) - 1))]