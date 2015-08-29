#!/usr/bin/env python3

import re

import wikipedia

from .utilities import BasePlugin

class WikiPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        match = re.search(r"^\s*\b(?:what\s+(?:is|are)|what's|wtf\s+(?:is|are))\s+([^,\?]+|\"[^\"]+\")", text, re.IGNORECASE)
        if not match: return False
        query = match.group(1)
        if query in {"this", "that", "going on", "up"}: return False # ignore these common false positive expressions

        # perform Wikipedia lookup
        try:
            self.respond("wikipedia says, \"{}\"".format(wikipedia.summary(query, sentences=2)))
        except wikipedia.exceptions.DisambiguationError as e: # disambiguation page, list possibilities
            self.respond("could be one of the following: " + "; ".join(e.args[1]))
        except:
            self.respond("dunno")
        return True
