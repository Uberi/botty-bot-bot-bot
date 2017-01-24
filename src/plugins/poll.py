#!/usr/bin/env python3

import re

from .utilities import BasePlugin
from .utilities import untag_word

class PollPlugin(BasePlugin):
    """
    Polling plugin for Botty.

    Per-channel polling, with one vote per user.

    Example invocations:

        #general    | Me: poll start stuff?
        #general    | Botty: *POLL STARTED:* stuff?
        • Say `poll y` to publicly agree
        • Say `poll n` to publicly disagree
        • Say `poll status` to check results
        #general    | Me: poll yep
        #general    | Me: poll status
        #general    | Botty: *POLL STATUS:* stuff?
        of the 1 people who voted, 1 people agree (100%), and 0 disagree (0%)
        `|####################################################################################################|`
        > *Me* votes yes
        #general    | Me: poll secret test
        #general    | Botty: *ANONYMOUS POLL STARTED:* test
        • Say `/msg @botty poll y #POLL_CHANNEL` to secretly agree
        • Say `/msg @botty poll n #POLL_CHANNEL` to secretly disagree
        • Say `poll status` to check results
        #general    | Me: poll check
        #general    | Botty: *POLL STATUS:* test
        Nobody voted :(
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.current_polls = {} # mapping from channel IDs to poll entries

    def on_message(self, m):
        if not m.is_user_message: return False
        user_name = self.get_user_name_by_id(m.user_id)

        # reaction voting
        if m.is_reaction_addition and m.user_id != self.get_bot_user_id():
            if m.channel_id not in self.current_polls: return False # check if reaction was posted in a channel with an active poll
            message_timestamp = self.current_polls[m.channel_id]["message_timestamp"]
            try: # check if message is a reaction on the poll message
                if m.timestamp != message_timestamp: return False
            except ValueError: # reaction doesn't have a timestamp
                return False

            if m.reaction == "+1": # vote to agree
                self.current_polls[m.channel_id]["user_votes"][user_name] = 1
                return True
            elif m.reaction == "-1": # vote to disagree
                self.current_polls[m.channel_id]["user_votes"][user_name] = 0
                return True
            return False

        # after this point, we only want to handle text messages
        if not m.is_user_text_message: return False

        # poll starting commands
        match = re.search(r"^\s*\bpoll\s+(?:start|begin|create)\b(?:\s+(.+))?", m.text, re.IGNORECASE)
        if match:
            description = match.group(1)

            message_timestamp = self.respond_complete(
                ("*POLL STARTED*\n" if description is None else "*POLL STARTED:* {}\n".format(description)) +
                "\u2022 React with :+1: or say `poll y` to publicly agree\n" +
                "\u2022 React with :-1: or say `poll n` publicly disagree\n" +
                "\u2022 Say `poll status` to check results"
            )

            self.current_polls[m.channel_id] = {
                "description": description,
                "user_votes": {},
                "is_secret": False,
                "message_timestamp": message_timestamp,
            }

            # add reactions so people can click on them
            self.react(m.channel_id, message_timestamp, "+1")
            self.react(m.channel_id, message_timestamp, "-1")

            return True
        match = re.search(r"^\s*\bpoll\s+(?:private|privately|secret|secretly|anon|anonymous|anonymously)\b(?:\s+(.+))?", m.text, re.IGNORECASE)
        if match:
            description = match.group(1)

            self.respond(
                ("*ANONYMOUS POLL STARTED*\n" if description is None else "*ANONYMOUS POLL STARTED:* {}\n".format(description)) +
                "\u2022 Say `/msg @botty poll y #POLL_CHANNEL` to secretly agree\n" +
                "\u2022 Say `/msg @botty poll n #POLL_CHANNEL` to secretly disagree\n" +
                "\u2022 Say `poll status` to check results"
            )

            self.current_polls[m.channel_id] = {
                "description": description,
                "user_votes": {},
                "is_secret": True,
                "message_timestamp": None,
            }
            return True

        # poll voting command
        match_y = re.search(r"^\s*\bpoll\s+(?:y|ye+s+|yeah?|su+re+|ye+p|yee+|yah?)\b(?:\s+(\S+))?", m.text, re.IGNORECASE)
        match_n = re.search(r"^\s*\bpoll\s+(?:n|no+|na+h?|no+pe|nay)\b(?:\s+(\S+))?", m.text, re.IGNORECASE)
        if match_y or match_n:
            new_channel_name = (match_y or match_n).group(1)
            if new_channel_name is not None:
                new_channel = self.get_channel_id_by_name(new_channel_name)
                if new_channel is None:
                    self.respond("what kind of channel is \"{}\" anyway".format(new_channel_name))
                    return True
            else:
                new_channel = m.channel_id

            if new_channel not in self.current_polls:
                self.respond_raw("there's no poll going on right now in {}".format(self.get_channel_name_by_id(new_channel)), as_thread=True)
                return True

            self.current_polls[new_channel]["user_votes"][user_name] = 1 if match_y else 0 # apply the vote
            return True

        # poll checking command
        match = re.search(r"^\s*\bpoll\s+(?:check|status|ready)\b", m.text, re.IGNORECASE)
        if match:
            if m.channel_id not in self.current_polls:
                self.respond_raw("there's no poll going on right now in {}".format(self.get_channel_name_by_id(m.channel_id)), as_thread=True)
                return True

            poll = self.current_polls[m.channel_id]
            voters = poll["user_votes"]
            if not voters:
                self.respond(("*POLL STATUS*\n" if poll["description"] is None else "*POLL STATUS:* {}\n".format(poll["description"])) + "Nobody voted :(")
                return True
            agree = sum(voters.values())
            disagree = len(voters) - agree
            agree_percent, disagree_percent = round(100 * agree / len(voters)), round(100 * disagree / len(voters))
            if poll["is_secret"]:
                self.respond(
                    ("*ANONYMOUS POLL STATUS*\n" if poll["description"] is None else "*ANONYMOUS POLL STATUS:* {}\n".format(poll["description"])) +
                    "of the {} people who voted, {} people agree ({}%), and {} disagree ({}%)\n".format(
                        len(voters), agree, agree_percent, disagree, disagree_percent
                    ) + "`|" + agree_percent * "#" + (100 - agree_percent) * "-"  + "|`"
                )
            else:
                self.respond(
                    ("*POLL STATUS*\n" if poll["description"] is None else "*POLL STATUS:* {}\n".format(poll["description"])) +
                    "of the {} people who voted, {} people agree ({}%), and {} disagree ({}%)\n".format(
                        len(voters), agree, agree_percent, disagree, disagree_percent
                    ) + "`|" + agree_percent * "#" + (100 - agree_percent) * "-"  + "|`\n" +
                    "\n".join("> *{}* votes {}".format(untag_word(user_name), "yes" if vote else "no") for user_name, vote in voters.items())
                )
            return True

        return False
