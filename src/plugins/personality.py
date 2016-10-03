#!/usr/bin/env python3

import re, random
from collections import defaultdict

from .utilities import BasePlugin

class PersonalityPlugin(BasePlugin):
    """
    Personality plugin for Botty.

    Adds a help command, responds to being thanked, and repeats things if two people say the same thing one after the other.

    Example invocations:

        #general    | Me: botty help
        #general    | Botty: botty's got you covered yo
        say `botty help` to get a light bedtime read
        say `calc SYMPY_EXPRESSION` to do some math
        say `botty what's SOMETHING` if you're too lazy to open a new tab and go to Wikipedia
        say `botty PHRASE` if you don't mind the echoes
        say `pls haiku me` if you're feeling poetic
        say `poll start DESCRIPTION` if y'all gotta decide something
        say `poll secret DESCRIPTION` if ya gotta do that, but like, anonymously
        say `sup botty` if you're wondering where the haps are
        say `yo botty` to receive some :fire: lines
        say `botty remind CHANNEL NATURAL_LANGUAGE_TIMES: DESCRIPTION` if you want reminders
        say `botty unremind DESCRIPTION` if you don't
        say `embiggenify TEXT` if your typing is too quiet
        say `uw course COURSE1, COURSE2, ...` if your schedule needs some padding
        say `quote me SOMETHING` if you're, like, a professional quote maker or something
        say `thanks botty`, just because you should
        #general    | Me: thanks botty
        #general    | Botty: don't mention it
        #general    | Other: test
        #general    | Me: test
        #general    | Botty: test
        #general    | Me: ???
        #general    | Botty: ????
    """
    def __init__(self, bot):
        super().__init__(bot)
        
        self.last_entries = {} # mapping from channel IDs to [last message in that channel, sender of last message, number of repetitions]
        self.message_repeated_threshold = 2 # minimum number of message repeats in a channel before we repeat it as well

        self.simple_pattern_actions = {
            r"(?i)\bbotty\s+(?:help|halp|\?+)\b":    lambda match: self.respond_raw(
                "botty's got you covered yo\n"
                "say `botty help` to get a light bedtime read\n"
                "say `calc SYMPY_EXPRESSION` to do some math\n"
                "say `botty what's SOMETHING` if you're too lazy to open a new tab and go to Wikipedia\n"
                "say `botty PHRASE` if you don't mind the echoes\n"
                "say `pls haiku me` if you're feeling poetic\n"
                "say `poll start DESCRIPTION` if y'all gotta decide something\n"
                "say `poll secret DESCRIPTION` if ya gotta do that, but like, anonymously\n"
                "say `sup botty` if you're wondering where the haps are\n"
                "say `yo botty` to receive some :fire: lines"
                "say `embiggenify TEXT` if your typing is too quiet\n"
                "say `uw course COURSE1, COURSE2, ...` if your schedule needs some padding\n"
                "say `quote me SOMETHING` if you're, like, a professional quote maker or something\n"
                "say `pls agar me PLAYER1, PLAYER2, ...` if you hate being productive (`<`/`>` to move, `<-`/`>-` to fire mass, `</`/`>/` to split)\n"
                "say `thanks botty`, just because you should"
                "plus a bunch of other secret ~bugs~ undocumented features to discover"
            ),
            r"(?i)\b(?:thanks|thx|ty)\b.*\bbotty\b": lambda match: self.respond_raw(random.choice(
                ["np", "np br0", "no prob", "don't mention it", "anytime"]
            )),
            r"(?i)^\s*(\?+)\s*$":               lambda match: self.reply("question"),
            r"(?i)^\s*(!+)\s*$":                lambda match: self.reply("exclamation"),
            r"(?i)\bdrink\s+some\s+water\b":    lambda match: self.reply("water_buffalo"),
            r"(?i)\bfor\s+the\s+(cd|record)\b": lambda match: self.reply("cd"),
            r"(?i)\begg":                       lambda match: self.reply("eggplant"),
            r"(?i)\b(nugget|nugs?|chicken)\b":  lambda match: self.reply("chicken"),
            r"(?i)\b(sna+kes?|sneks?)\b":       lambda match: self.reply("snake"),
            r"(?i)\baha\b":                     lambda match: self.reply("aha"),
        }

    def on_message(self, message):
        text, channel, user = self.get_message_text(message), self.get_message_channel(message), self.get_message_sender(message)
        if text is None or channel is None or user is None: return False

        # compute the number of times different people have repeated it
        if channel in self.last_entries and text == self.last_entries[channel][0] and user != self.last_entries[channel][1]:
            self.last_entries[channel][2] += 1
        else:
            self.last_entries[channel] = [text, user, 1]

        for pattern, action in self.simple_pattern_actions.items():
            match = re.search(pattern, text)
            if match:
                action(match)
                return True

        if random.random() < 0.005:
            self.reply(random.choice(["lenny", "boredparrot", "pugrun", "chart_with_downwards_trend"]))

        # repeat this message if other people have repeated it enough times, 50% of the time
        if self.last_entries[channel][2] >= self.message_repeated_threshold and random.random() < 0.5:
            self.respond(text) # repeat the message
            del self.last_entries[channel]
            return True

        if re.search(r"^\s*(?:I\s+think|imo|if\s+you\s+ask\s+me)\b", text, re.IGNORECASE) and random.random() < 0.01:
            user_name = self.get_user_name_by_id(user)
            self.respond_raw(random.choice(["nah", "{}, I disagree".format(user_name), "I don't think so {}".format(user_name), "I doubt that {}".format(user_name)]))
            return True

        return False
