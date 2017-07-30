#!/usr/bin/env python3

import os, re, json
import sqlite3

from markov import Markov

SQLITE_DATABASE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "chains.db")
CHAT_HISTORY_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "@history")

def get_metadata():
    with open(os.path.join(CHAT_HISTORY_DIRECTORY, "metadata", "users.json"), "r") as f:
        entries = json.load(f)
        user_names = {entry["id"]: entry["name"] for entry in entries}
        user_real_names = {entry["id"]: entry["profile"]["real_name"] for entry in entries}
    with open(os.path.join(CHAT_HISTORY_DIRECTORY, "metadata", "channels.json"), "r") as f:
        entries = json.load(f)
        channel_names = {entry["id"]: entry["name"] for entry in entries}
    return user_names, user_real_names, channel_names

USER_NAMES_BY_ID, USER_REAL_NAMES_BY_ID, CHANNEL_NAMES_BY_ID = get_metadata()

def server_text_to_text(server_text):
    """Returns `server_text`, a string in Slack server message format, converted into a plain text string. The transformation can lose some information for escape sequences, such as link labels."""
    assert isinstance(server_text, str), "`server_text` must be a string rather than \"{}\"".format(server_text)
    text_without_special_sequences = re.sub(r"<[^<>]*>", "", server_text)
    assert "<" not in text_without_special_sequences and ">" not in text_without_special_sequences, "Invalid special sequence in server text \"{}\", perhaps some text needs to be escaped"

    # process link references
    def process_special_sequence(match):
        original, body = match.group(0), match.group(1).split("|")[0]
        if body.startswith("#"): # channel reference
            return "#" + CHANNEL_NAMES_BY_ID[body[1:]] if body[1:] in CHANNEL_NAMES_BY_ID else original
        if body.startswith("@"): # user reference
            return "@" + USER_NAMES_BY_ID[body[1:]] if body[1:] in USER_NAMES_BY_ID else original
        if body.startswith("!"): # special command
            if body == "!channel": return "@channel"
            if body == "!group": return "@group"
            if body == "!everyone": return "@everyone"
        return body # link, should remove angle brackets and label in order to allow it to linkify
    raw_text = re.sub(r"<(.*?)>", process_special_sequence, server_text)

    return raw_text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

def get_message_text(message):
    """Returns the text value of `message` if it is a valid text message, or `None` otherwise"""
    if message.get("type") == "message" and isinstance(message.get("ts"), str):
        if isinstance(message.get("text"), str) and isinstance(message.get("user"), str): # normal message
            return server_text_to_text(message["text"])
        if message.get("subtype") == "message_changed" and isinstance(message.get("message"), dict) and isinstance(message["message"].get("user"), str) and isinstance(message["message"].get("text"), str): # edited message
            return server_text_to_text(message["message"]["text"])
    return None

def get_history_files():
    """Returns a mapping from channel IDs to absolute file paths of their history entries"""
    for dirpath, _, filenames in os.walk(CHAT_HISTORY_DIRECTORY):
        result = {}
        for history_file in filenames:
            channel_id, extension = os.path.splitext(os.path.basename(history_file))
            if extension != ".json": continue
            result[channel_id] = os.path.join(dirpath, history_file)
        return result
    return {}

connection = sqlite3.connect(SQLITE_DATABASE)
connection.execute("DROP TABLE IF EXISTS counts")
connection.execute("DROP TABLE IF EXISTS chain")
connection.execute("CREATE TABLE counts (key TEXT PRIMARY KEY, count INTEGER)")
connection.execute("CREATE TABLE chain (key TEXT, next_word TEXT, occurrences INTEGER)")
connection.execute("CREATE INDEX chain_key_index ON chain (key)")

markov = Markov(2) # Markov model with 2 word look-behind
for channel_id, history_file in get_history_files().items():
    with open(history_file, "r") as f:
        for entry in f:
            text = get_message_text(json.loads(entry))
            if text is not None:
                markov.train(Markov.tokenize_text(text))

connection.executemany(
    "INSERT INTO counts VALUES (?, ?)",
    (("\n".join(key), occurrences) for key, occurrences in markov.counts.items())
)
connection.executemany(
    "INSERT INTO chain VALUES (?, ?, ?)",
    (("\n".join(key), next_word, occurrences) for key, next_mapping in markov.chain.items()
                                   for next_word, occurrences in next_mapping.items())
)

connection.commit()
connection.close()
