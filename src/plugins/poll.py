#!/usr/bin/env python3

import re

from .utilities import BasePlugin

class PollPlugin(BasePlugin):
    """
    Polling plugin for Botty.

    Per-channel polling, with one vote per user.

    Example invocations:

        #general    | Me: poll start stuff?
        #general    | Botty: *POLL STARTED:* stuff?
        • Say `poll y` to publicly agree, or `/msg @botty poll y #POLL_CHANNEL` to secretly agree
        • Say `poll n` to publicly disagree, or `/msg @botty poll n #POLL_CHANNEL` to secretly disagree
        • Say `poll done` to finish
        #general    | Me: poll yep
        #general    | Me: poll status
        #general    | Botty: *POLL COMPLETED:* stuff?
        of the 1 people who voted, 1 people agree (100%), and 0 disagree (0%)
        `|####################################################################################################|`
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.current_polls = {}

    def on_message(self, message):
        text, channel, user = self.get_message_text(message), self.get_message_channel(message), self.get_message_sender(message)
        if text is None or channel is None or user is None: return False

        # poll starting command
        match = re.search(r"^\s*\bpoll\s+(?:start|begin|create)\b(?:\s+(.+))?", text, re.IGNORECASE)
        if match:
            description = match.group(1)
            self.current_polls[channel] = [0, 0, description, set()]

            self.respond(
                ("*POLL STARTED*\n" if description is None else "*POLL STARTED:* {}\n".format(description)) +
                "\u2022 Say `poll y` to publicly agree, or `/msg @botty poll y #POLL_CHANNEL` to secretly agree\n" +
                "\u2022 Say `poll n` to publicly disagree, or `/msg @botty poll n #POLL_CHANNEL` to secretly disagree\n" +
                "\u2022 Say `poll status` to check results"
            )
            return True

        # poll voting command
        match_y = re.search(r"^\s*\bpoll\s+(?:y|yes|yeah?|sure|yep|yee+|yah?)\b(?:\s+(\S+))?", text, re.IGNORECASE)
        match_n = re.search(r"^\s*\bpoll\s+(?:n|no|na+h?|nope|nay)\b(?:\s+(\S+))?", text, re.IGNORECASE)
        if match_y or match_n:
            new_channel_name = (match_y or match_n).group(1)
            if new_channel_name is not None:
                new_channel = self.get_channel_id_by_name(new_channel_name)
                if new_channel is None:
                    self.respond("what kind of channel is \"{}\" anyway".format(new_channel_name))
                    return True
                channel = new_channel

            if channel not in self.current_polls:
                self.respond_raw("there's no poll going on right now in {}".format(self.get_channel_name_by_id(channel)))
                return True

            user_name = self.get_user_name_by_id(user)
            if user_name in self.current_polls[channel][3]:
                self.respond_raw("nice try {}".format(user_name))
                return True
            self.current_polls[channel][3].add(user_name)

            if match_y:
                self.current_polls[channel][1] += 1
            else:
                self.current_polls[channel][0] += 1
            return True

        # poll completing command
        match = re.search(r"^\s*\bpoll\s+(?:check|status|ready)\b", text, re.IGNORECASE)
        if match:
            if channel not in self.current_polls:
                self.respond_raw("there's no poll going on right now in {}".format(self.get_channel_name_by_id(channel)))
                return True

            poll = self.current_polls[channel]
            disagree, agree, description = poll[0], poll[1], poll[2]
            total = agree + disagree
            if total == 0:
                self.respond(("*POLL COMPLETED*\n" if description is None else "*POLL COMPLETED:* {}\n".format(description)) + "Nobody voted :(")
                return True
            agree_percent = round(100 * agree / total)
            self.respond(
                ("*POLL COMPLETED*\n" if description is None else "*POLL COMPLETED:* {}\n".format(description)) +
                "of the {} people who voted, {} people agree ({}%), and {} disagree ({}%)\n".format(total, agree, agree_percent, disagree, round(100 * disagree / total)) +
                "`|" + agree_percent * "#" + (100 - agree_percent) * "-"  + "|`"
            )
            return True

        return False
