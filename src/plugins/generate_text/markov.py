import re, random
from collections import defaultdict

class Markov:
    PUNCTUATION = r"[`~@#$%_\\'+\-/]" # punctuation that is a part of text
    STANDALONE = r"(?:[!.,;()^&\[\]{}|*=<>?]|[dDpP][:8]|:\S)" # standalone characters or emoticons that wouldn't otherwise be captured
    WORD_PATTERN = STANDALONE + r"\S*|https?://\S+|(?:\w|" + PUNCTUATION + r")+" # token pattern
    word_matcher = re.compile(WORD_PATTERN, re.IGNORECASE)

    def __init__(self, lookbehind_length = 2):
        self.lookbehind_length = lookbehind_length

        self.chain = defaultdict(lambda: defaultdict(int))
        self.counts = defaultdict(int)

    @staticmethod
    def tokenize_text(text):
        return [m.lower() for m in Markov.word_matcher.findall(text)]
    @staticmethod
    def format_words(token_list): # formats a list of words into a human-readable sentence string
        close_matcher = re.compile("[!.,;:)\]}?]", re.IGNORECASE)
        phrase = ""
        for i, v in enumerate(token_list):
            if i == 0 or close_matcher.match(v): phrase += v
            else: phrase += " " + v
        return phrase

    def train(self, message, importance = 1):
        # find chain counts as a dictionary mapping tokens to dictionaries mapping tokens to amount of times they appear after the first token
        current_key = ()
        for i, token in enumerate(message): # loop through every index except the highest one
            self.chain[current_key][token] += importance # update the Markov model with current token
            self.counts[current_key] += importance
            
            if i < self.lookbehind_length: current_key += (token,) # add current token to key if just starting
            else: current_key = current_key[1:] + (token,) # shift token onto key if inside message

        self.chain[current_key][None] += importance # update the Markov model with end of message
        self.counts[current_key] += importance

    def speak(self, initial_state = ()):
        if len(self.counts) == 0: raise ValueError("Markov model is not trained yet")
        
        # generate a message based on probability chains
        current_key = tuple(initial_state)[-self.lookbehind_length:]
        token_list = []
        while True:
            # pick a random token weighted on the number of times it has occurred previously
            if current_key not in self.chain: raise KeyError("Key not in chain: {}".format(current_key))
            choices = self.chain[current_key]
            random_choice = random.randrange(0, self.counts[current_key])
            for current_choice, occurrences in choices.items():
                random_choice -= occurrences
                if random_choice < 0:
                    new_token = current_choice
                    break
            else: # couldn't find the choice somehow
                raise ValueError("Bad choice for key: {}".format(current_key)) # this should never happen but would otherwise be hard to detect if it did

            # add the token to the message
            if new_token == None: break
            token_list.append(new_token)

            if len(current_key) < self.lookbehind_length: current_key += (new_token,) # add current token to key if just starting
            else: current_key = current_key[1:] + (new_token,) # shift token onto key if inside message
        return token_list
