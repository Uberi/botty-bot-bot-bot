#!/usr/bin/env python3

import re
from collections import defaultdict

from .utilities import BasePlugin

class PersonalityPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        
        self.channel_last_message = {} # mapping from channel IDs to the last message in that channel
        self.channel_last_message_repetitions = {} # mapping from channel IDs to the number of times the last message has been repeated
        self.message_repeated_threshold = 2 # minimum number of message repeats in a channel before we repeat it as well

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        if "channel" not in message: return False
        channel = message["channel"]

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
            self.respond("np")
            return True

        # repeat this message if other people are repeating it
        if text == self.channel_last_message.get(channel):
            self.channel_last_message_repetitions[channel] += 1
            if self.channel_last_message_repetitions[channel] >= self.message_repeated_threshold:
                self.respond(text) # repeat the message
                del self.channel_last_message[channel]
                del self.channel_last_message_repetitions[channel]
        else:
            self.channel_last_message_repetitions[channel] = 1
            self.channel_last_message[channel] = text
        return False
