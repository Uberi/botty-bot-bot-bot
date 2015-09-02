#!/usr/bin/env python3

import os, json, re, random

from ..utilities import BasePlugin

PUNCTUATION = r"[`~@#$%_\\'+\-/]" # punctuation that is a part of text
STANDALONE = r"(?:[!.,;()^&\[\]{}|*=<>?]|[dDpP][:8]|:\S)" # standalone characters or emoticons that wouldn't otherwise be captured
WORD_PATTERN = STANDALONE + r"\S*|https?://\S+|(?:\w|" + PUNCTUATION + r")+" # token pattern
WORD_MATCHER = re.compile(WORD_PATTERN, re.IGNORECASE)
def tokenize_text(text):
    return (m.lower() for m in WORD_MATCHER.findall(text))

def load_word_syllable_counts():
    word_syllable_counts = {}
    hyphenation_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "mhyph.txt")
    with open(hyphenation_file, "rb") as f:
        for line in f.readlines():
            try: word = line.rstrip(b"\r\n").replace(b"\xA5", b"").decode("UTF-8")
            except UnicodeDecodeError: continue
            syllables = 1 + line.count(b"\xA5") + line.count(b" ") + line.count(b"-")
            word_syllable_counts[word] = syllables
    return word_syllable_counts

class HaikuPlugin(BasePlugin):
    """
    Haiku generator plugin for Botty.

    Here, haikus are defined as three sentences with five, seven, and five syllables, respectively.

    The `mhyph.txt` file is the [MOBY Hyphenation List](http://www.gutenberg.org/ebooks/3204), taken from the MOBY English language project.

    Example invocations:

        #general    | Me: pls haiku me
        #general    | Botty: ```
        but for good reason
        something something teleport
        that thing with that guy
        ```
        #general    | Me: pls haiku me
        #general    | Botty: ```
        that's pretty good news
        but you can control that stuff
        "accidentally"
        ```
    """
    def __init__(self, bot):
        super().__init__(bot)

        self.five_syllable_messages = []
        self.seven_syllable_messages = []

        # find messages with 5 syllables and 7 syllables
        self.logger.info("loading syllable dictionary...")
        word_syllable_counts = load_word_syllable_counts()
        self.logger.info("processing history...")
        for channel_name, history_file in self.get_history_files().items():
            with open(history_file, "r") as f:
                for entry in f:
                    text = self.get_message_text(json.loads(entry))
                    if text is None: continue

                    # count syllables in the text
                    syllables = 0
                    for token in tokenize_text(text):
                        if token in word_syllable_counts:
                            syllables += word_syllable_counts[token]
                        else: # unknown word, ignore the whole message
                            break
                    else:
                        if syllables == 5:
                            self.five_syllable_messages.append(text)
                        elif syllables == 7:
                            self.seven_syllable_messages.append(text)

    def on_message(self, message):
        text = self.get_message_text(message)
        if text is None: return False
        if not re.search(r"\bpls\s+haiku\s+me\b", text, re.IGNORECASE): return False

        # generate haiku
        self.respond_raw("```\n{}\n{}\n{}\n```".format(
            random.choice(self.five_syllable_messages),
            random.choice(self.seven_syllable_messages),
            random.choice(self.five_syllable_messages)
        ))
        return True
