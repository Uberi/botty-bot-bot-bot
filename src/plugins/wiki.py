#!/usr/bin/env python3

"""
Wikipedia lookup plugin for Botty.

Example invocations:

    #general    | Me: what is fire
    #general    | Botty: wikipedia says, "Fire is the rapid oxidation of a material in the exothermic chemical process of combustion, releasing heat, light, and various reaction products. Slower oxidative processes like rusting or digestion are not included by this definition."
    #general    | Me: what's bismuth?
    #general    | Botty: wikipedia says, "Bismuth is a chemical element with symbol Bi and atomic number 83. Bismuth, a pentavalent post-transition metal, chemically resembles arsenic and antimony. Elemental bismuth may occur naturally, although its sulfide and oxide form important commercial ores."
    #general    | Me: wtf is water
    #general    | Botty: wikipedia says, "Water (chemical formula: H2O) is a transparent fluid which forms the world's streams, lakes, oceans and rain, and is the major constituent of the fluids of organisms. As a chemical compound, a water molecule contains one oxygen and two hydrogen atoms that are connected by covalent bonds."
"""

import re

import wikipedia

from .utilities import BasePlugin

class WikiPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, message):
        text = self.get_message_text(message)
        if text is None: return False
        match = re.search(r"^\s*\b(?:what\s+is|what's|wtf\s+(?:is|are))\s+([^,\?]+|\"[^\"]+\")", text, re.IGNORECASE)
        if not match: return False
        query = self.sendable_text_to_text(match.group(1)) # get query as plain text in order to make things like < and > work (these are usually escaped)
        if query in {"this", "that", "going on", "up"}: return False # ignore these common false positive expressions

        # perform Wikipedia lookup
        try:
            self.respond_raw("wikipedia says, \"{}\"".format(wikipedia.summary(query, sentences=2)))
        except wikipedia.exceptions.DisambiguationError as e: # disambiguation page, list possibilities
            self.respond_raw("could be one of the following: {}".format("; ".join(e.args[1])))
        except:
            self.respond_raw("dunno")
        return True
