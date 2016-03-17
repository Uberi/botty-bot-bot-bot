#!/usr/bin/env python3

import os, json, re
import sqlite3

from markov import Markov

# generate and print a large number of phrases using Slack history mixed with the KJV bible for amusing quotes

CHAT_HISTORY_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "@history")

def server_text_to_sendable_text(server_text):
    """Returns `server_text`, a string in Slack server message format, converted into a string in Slack sendable message format."""
    assert isinstance(server_text, str), "`server_text` must be a string rather than \"{}\"".format(server_text)
    text_without_special_sequences = re.sub(r"<[^<>]*>", "", server_text)
    assert "<" not in text_without_special_sequences and ">" not in text_without_special_sequences, "Invalid special sequence in server text \"{}\", perhaps some text needs to be escaped"

    # process link references
    def process_special_sequence(match):
        original, body = match.group(0), match.group(1).split("|")[0]
        if body.startswith("#C"): return original # channel reference, should send unchanged
        if body.startswith("@U"): return original # user reference, should send unchanged
        if body.startswith("!"): return original # special command, should send unchanged
        return body # link, should remove angle brackets and label in order to allow it to linkify
    return re.sub(r"<(.*?)>", process_special_sequence, server_text)

def sendable_text_to_text(sendable_text):
    """Returns `sendable_text`, a string in Slack sendable message format, converted into a plain text string. The transformation can lose some information for escape sequences, such as link labels."""
    assert isinstance(sendable_text, str), "`sendable_text` must be a string rather than \"{}\"".format(sendable_text)
    text_without_special_sequences = re.sub(r"<[^<>]*>", "", sendable_text)
    assert "<" not in text_without_special_sequences and ">" not in text_without_special_sequences, "Invalid special sequence in sendable text \"{}\", perhaps some text needs to be escaped"

    # process link references
    def process_special_sequence(match):
        original, body = match.group(0), match.group(1).split("|")[0]
        if body.startswith("#C"): # channel reference
            return body
        if body.startswith("@U"): # user reference
            return body
        if body.startswith("!"): # special command
            if body == "!channel": return "@channel"
            if body == "!group": return "@group"
            if body == "!everyone": return "@everyone"
        return original
    raw_text = re.sub(r"<(.*?)>", process_special_sequence, sendable_text)

    return raw_text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def get_history_files():
    """Returns a mapping from channel names to absolute file paths of their history entries"""
    for dirpath, _, filenames in os.walk(CHAT_HISTORY_DIRECTORY):
        result = {}
        for history_file in filenames:
            channel_name, extension = os.path.splitext(os.path.basename(history_file))
            if extension != ".json": continue
            result["#" + channel_name] = os.path.join(dirpath, history_file)
        return result
    return {}

def get_message_text(message):
    """Returns the text value of `message` if it is a valid text message, or `None` otherwise"""
    if message.get("type") == "message" and isinstance(message.get("ts"), str):
        if isinstance(message.get("text"), str) and isinstance(message.get("user"), str): # normal message
            return server_text_to_sendable_text(message["text"])
        if message.get("subtype") == "message_changed" and isinstance(message.get("message"), dict) and isinstance(message["message"].get("user"), str) and isinstance(message["message"].get("text"), str): # edited message
            return server_text_to_sendable_text(message["message"]["text"])
    return None

markov = Markov(2) # Markov model with 2 word look-behind

entries = open("kjv.txt", "r").read().split("\n")
matcher = re.compile(Markov.WORD_PATTERN, re.IGNORECASE)
for message in (matcher.findall(m) for m in entries):
    markov.train([m.lower() for m in message], 3)

for channel_name, history_file in get_history_files().items():
    with open(history_file, "r") as f:
        for entry in f:
            text = get_message_text(json.loads(entry))
            if text is not None:
                markov.train(Markov.tokenize_text(sendable_text_to_text(text)))

for x in range(10000):
    print(Markov.format_words(markov.speak()))