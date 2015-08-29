#!/usr/bin/env python3

import re

from .utilities import BasePlugin

class PollPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.current_polls = {}

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        if "channel" not in message: return False
        channel = message["channel"]
        user_name = self.get_user_name_by_id(message["user"])

        match = re.search(r"^\s*\bpoll\s+start(?:\s+(.+))?\b", text, re.IGNORECASE)
        if match:
            description = match.group(1)
            self.current_polls[channel] = [0, 0, description, set()]

            if description is None: self.respond("poll started (say `poll y` to agree, `poll n` to disagree, and `poll done` to finish; vote secretly by DM'ing botty with `poll y #POLL_CHANNEL` or `poll n #POLL_CHANNEL`)")
            else: self.respond("poll started: \"{}\" (say `poll y` to agree, `poll n` to disagree, and `poll done` to finish; vote secretly by DM'ing botty with `poll y #POLL_CHANNEL` or `poll n #POLL_CHANNEL`)".format(description))
            return True

        match_y = re.search(r"^\s*\bpoll\s+(?:y|yes|yeah?|sure|yep|yee+|yah?)\b(?:\s+(\S+))?", text, re.IGNORECASE)
        match_n = re.search(r"^\s*\bpoll\s+(?:n|no|na+h?|nope|nay)\b(?:\s+(\S+))?", text, re.IGNORECASE)
        if match_y or match_n:
            new_channel_name = (match_y or match_n).group(1)
            if new_channel_name is not None:
                new_channel = self.get_channel_id_by_name(new_channel_name.strip())
                if new_channel is None:
                    self.respond("what kind of channel is \"{}\" anyway".format(channel_name))
                    return True
                channel = new_channel

            if channel not in self.current_polls:
                self.respond("there's no poll going on right now in #{}".format(self.get_channel_name_by_id(channel)))
                return True

            if user_name in self.current_polls[channel][3]:
                self.respond("nice try {}".format(user_name))
                return True
            self.current_polls[channel][3].add(user_name)

            if match_y:
                self.current_polls[channel][1] += 1
                if self.current_polls[channel][2] is None: self.respond("{} agreed".format(user_name))
                else: self.respond("{} agreed with \"{}\"".format(user_name, self.current_polls[channel][2]))
            else:
                self.current_polls[channel][0] += 1
                if self.current_polls[channel][2] is None: self.respond("{} disagreed".format(user_name))
                else: self.respond("{} disagreed with \"{}\"".format(user_name, self.current_polls[channel][2]))
            return True

        match = re.search(r"^\s*\bpoll\s+(?:close|finish|done|status|complete|ready)\b", text, re.IGNORECASE)
        if match:
            if channel not in self.current_polls:
                self.respond("there's no poll going on right now in #{}".format(self.get_channel_name_by_id(channel)))
                return True

            if match_y:
                self.current_polls[channel][1] += 1
                if self.current_polls[channel][2] is None: self.respond("{} agreed".format(user_name))
                else: self.respond("{} agreed with \"{}\"".format(user_name, self.current_polls[channel][2]))
            elif match_n:
                self.current_polls[channel][0] += 1
                if self.current_polls[channel][2] is None: self.respond("{} disagreed".format(user_name))
                else: self.respond("{} disagreed with \"{}\"".format(user_name, self.current_polls[channel][2]))
            else:
                if self.current_polls[channel][2] is None: self.respond("poll closed - {} agree, {} disagree".format(self.current_polls[channel][1], self.current_polls[channel][0]))
                else: self.respond("poll \"{}\" closed - {} agree, {} disagree".format(self.current_polls[channel][2], self.current_polls[channel][1], self.current_polls[channel][0]))
            return True

        return False
