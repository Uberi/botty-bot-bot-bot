#!/usr/bin/env python3

import re, json
from os import path

from ..utilities import BasePlugin
from .markov import Markov

class GenerateTextPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

        self.logger.info("training Markov model...")
        self.markov = Markov(2) # Markov model with 2 word look-behind
        for channel_name, history_file in self.get_history_files().items():
            with open(history_file, "r") as f:
                for entry in f:
                    text = self.get_text_message_body(json.loads(entry))
                    if text is not None:
                        self.markov.train(Markov.tokenize_text(text))
        self.logger.info("Markov model training complete")

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        match = re.search(r"\bbotty[\s,\.]+(.*)", text, re.IGNORECASE)
        if not match: return False
        query = match.group(1)

        # use markov chain to complete given phrase
        try: self.respond(self.generate_sentence_starting_with(self.markov, query))
        except KeyError: self.respond(self.generate_sentence_starting_with(self.markov))
        return True

    # load Markov conversation model
    def generate_sentence_starting_with(self, markov, first_part = ""):
        first_part = first_part.strip()
        words = Markov.tokenize_text(first_part) if first_part != "" else []
        return Markov.format_words(words + markov.speak(words))
