#!/usr/bin/env python3

import re, random

from pyfiglet import Figlet

from .utilities import BasePlugin

class BigTextPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        match = re.search(r"^\s*\bembiggenify\s+(.{1,40})", text, re.IGNORECASE)
        if not match: return False
        query = match.group(1)

        # render the text in a random font
        good_fonts = [
            "stampatello",
            "stacey",
            "threepoint",
            "cricket",
            "puffy",
            "avatar",
            "contessa",
            "goofy",
            "smisome1",
            "serifcap",
            "mini",
            "smkeyboard",
            "bulbhead",
            "larry3d",
            "big",
            "thin",
            "nvscript",
            "isometric1",
            "isometric2",
            "georgia11",
            "epic",
            "crawford",
            "chunky",
            "isometric3",
            "isometric4",
        ]
        random_font = random.choice(good_fonts)
        f = Figlet(font=random_font)
        self.respond_raw("```{}```".format(f.renderText(query).rstrip()))
        return True
