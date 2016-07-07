#!/usr/bin/env python3

import re, random
from os import path

from ..utilities import BasePlugin

PARTS_OF_SPEECH_FILE = path.join(path.dirname(path.realpath(__file__)), "mobypos.txt")
PRONOUNCIATION_FILE = path.join(path.dirname(path.realpath(__file__)), "mobypron.txt")

class NowIAmDudePlugin(BasePlugin):
    """
    "I was born A but now I am B" plugin for Botty.

    Generates sentences of the form "I was born A but now I am B", where A is an adjective, B is a noun, and A and B rhyme.

    Uses `mobypos.txt` and `mobypron.txt` from the MOBY English language project (`mobypron.txt` is a copy of `mobyron.unc` in the original project, but re-encoded to UTF-8).

    Example invocations:

        #general    | Me: dude me
        #general    | Botty: I was born tender but now I am ascender
    """
    def __init__(self, bot):
        super().__init__(bot)

        vowel_sounds = {"a", "e", "i", "o", "u", "A", "E", "I", "O", "U", "aI", "eI", "Oi", "oU", "AU", "@", "(@)", "[@]", "&"}

        nouns, adjectives = [], []
        with open(PARTS_OF_SPEECH_FILE, "r") as f:
            for line in f:
                word, parts_of_speech = line.split("\\")
                if "A" in parts_of_speech: adjectives.append(word)
                if "N" in parts_of_speech: nouns.append(word)
        self.nouns, self.adjectives = nouns, adjectives

        last_syllable_words, word_last_syllables = {}, {}
        with open(PRONOUNCIATION_FILE, "r") as f:
            for line in f:
                word, pronounciation = line.split(" ", 1)
                syllables, index = [[]], 0
                for phoneme in pronounciation.strip("/\n").split("/"):
                    if phoneme in vowel_sounds:
                        index += 1
                        syllables.append([phoneme])
                    elif phoneme != "": # consonant sound
                        syllables[index].append(phoneme)
                if len(syllables[-1]) == 0: del syllables[-1] # delete last blank syllable if present
                if len(syllables) > 1: last_syllable = (tuple(syllables[-2]), tuple(syllables[-1]))
                else: last_syllable = tuple(syllables[-1])
                if last_syllable not in last_syllable_words: last_syllable_words[last_syllable] = []
                last_syllable_words[last_syllable].append(word)
                word_last_syllables[word] = last_syllable
        self.last_syllable_words, self.word_last_syllables = last_syllable_words, word_last_syllables

    def get_rhyming_pair(self):
        while True:
            first_word = random.choice(self.adjectives)
            if first_word not in self.word_last_syllables: continue # word is in part of speech dictionary, but not the pronounciation dictionary
            rhyming_words = self.last_syllable_words[self.word_last_syllables[first_word]]
            for word in rhyming_words:
                if word in self.nouns and word != first_word:
                    return first_word, word

    def on_message(self, message):
        text = self.get_message_text(message)
        if text is None: return False

        if re.search(r"\bdu+de+\s+me+\b", text, re.IGNORECASE):
            first, second = self.get_rhyming_pair()
            self.respond_raw("I was born {} but now I am {}".format(first, second))
            return True

        return False
