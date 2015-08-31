#!/usr/bin/env python3

import re, random
from collections import defaultdict

from .utilities import BasePlugin

class PersonalityPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        
        self.last_entries = {} # mapping from channel IDs to [last message in that channel, sender of last message, number of repetitions]
        self.message_repeated_threshold = 2 # minimum number of message repeats in a channel before we repeat it as well

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        if "channel" not in message or "user" not in message: return False
        channel, user = message["channel"], message["user"]

        if re.search(r"\bbotty\s+(?:help|halp|\?+)\b", text, re.IGNORECASE):
            self.respond(
                "botty's got you covered yo\n"
                "say `botty help` to get a light bedtime read\n"
                "say `calc SYMPY_EXPRESSION` to do some math\n"
                "say `what's SOMETHING` if you're too lazy to open a new tab and go to Wikipedia\n"
                "say `botty PHRASE` if you don't mind the echoes\n"
                "say `pls haiku me` if you're feeling poetic\n"
                "say `poll start DESCRIPTION` if y'all gotta decide something\n"
                "say `botty remind CHANNEL NATURAL_LANGUAGE_TIMES: DESCRIPTION` if you want reminders\n"
                "say `botty unremind DESCRIPTION` if you don't\n"
                "say `embiggenify TEXT` if your typing is too quiet\n"
                "say `thanks botty`, just because you should\n"
            )
            return True

        if re.search(r"\b(?:thanks|thx|ty)\b.*\bbotty\b", text, re.IGNORECASE):
            self.respond(random.choice("np", "np br0", "no prob", "don't mention it"))
            return True

        # compute the number of times different people have repeated it
        if channel in self.last_entries and text == self.last_entries[channel][0] and user != self.last_entries[channel][1]:
            self.last_entries[channel][2] += 1
        else:
            self.last_entries[channel] = [text, user, 1]

        # repeat this message if other people have repeated it enough times
        if self.last_entries[channel][2] >= self.message_repeated_threshold:
            self.respond(text) # repeat the message
            del self.last_entries[channel]
        return False
