#!/usr/bin/env python3

import re, random

from pyfiglet import Figlet

from .utilities import BasePlugin

class BigTextPlugin(BasePlugin):
    """
    ASCII art text plugin for Botty.

    Example invocations:

        #general    | Me: biggify hello
        #general    | Botty: ```                                               
         ,dPYb,              ,dPYb, ,dPYb,             
         IP'`Yb              IP'`Yb IP'`Yb             
         I8  8I              I8  8I I8  8I             
         I8  8'              I8  8' I8  8'             
         I8 dPgg,    ,ggg,   I8 dP  I8 dP    ,ggggg,   
         I8dP" "8I  i8" "8i  I8dP   I8dP    dP"  "Y8ggg
         I8P    I8  I8, ,8I  I8P    I8P    i8'    ,8I  
        ,d8     I8, `YbadP' ,d8b,_ ,d8b,_ ,d8,   ,d8'  
        88P     `Y8888P"Y8888P'"Y888P'"Y88P"Y8888P"```
        #general    | Me: embiggenify hello
        #general    | Botty: ```            
        |_  _ || _  
        | |(/_||(_)```
    """
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, m):
        if not m.is_user_text_message: return False
        match = re.search(r"^\s*\bbiggify\s+(.{1,40})", m.text, re.IGNORECASE)
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
        result = f.renderText(query).rstrip()
        if result == "": return False

        self.respond_raw("```{}```".format(result))
        return True
