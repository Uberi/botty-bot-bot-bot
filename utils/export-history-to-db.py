#!/usr/bin/env python3

import os, re, json
import sqlite3

SQLITE_DATABASE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "history.db")
CHAT_HISTORY_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "@history")

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
    if message.get("type") != "message": return None
    if not isinstance(message.get("user"), str): return None
    if not isinstance(message.get("text"), str): return None
    if not isinstance(message.get("ts"), str): return None
    return server_text_to_sendable_text(message["text"])

connection = sqlite3.connect(SQLITE_DATABASE)
connection.execute("DROP TABLE IF EXISTS messages")
connection.execute("DROP TABLE IF EXISTS users")
connection.execute("DROP TABLE IF EXISTS channels")
connection.execute("CREATE TABLE messages (timestamp INTEGER, timestamp_order INTEGER, channel_id TEXT, user_id TEXT, value TEXT, PRIMARY KEY (timestamp, timestamp_order, channel_id))")
connection.execute("CREATE TABLE users (user_id TEXT PRIMARY KEY, user_name TEXT, user_real_name TEXT, is_bot INTEGER)")
connection.execute("CREATE TABLE channels (channel_id TEXT PRIMARY KEY, channel_name TEXT, purpose TEXT)")

# export metadata
with open(os.path.join(CHAT_HISTORY_DIRECTORY, "metadata", "channels.json")) as f:
    CHANNELS = json.load(f)
with open(os.path.join(CHAT_HISTORY_DIRECTORY, "metadata", "users.json")) as f:
    USERS = json.load(f)
connection.executemany(
    "INSERT INTO users VALUES (?, ?, ?, ?)",
    ((user["id"], user["name"], user["real_name"], int(user["is_bot"])) for user in USERS if not user["deleted"])
)
connection.executemany(
    "INSERT INTO channels VALUES (?, ?, ?)",
    ((channel["id"], channel["name"], channel.get("purpose", {}).get("value")) for channel in CHANNELS if not channel["is_archived"])
)

# export messages
user_name_id = {user["name"]: user["id"] for user in USERS}
channel_name_id = {"#" + channel["name"]: channel["id"] for channel in CHANNELS}
def message_values(history_lines):
    for entry in history_lines:
        message = json.loads(entry)
        text = get_message_text(message)
        if text is not None:
            timestamp, timestamp_order = message["ts"].split(".")
            yield (timestamp, timestamp_order, channel_id, message["user"], text)
for channel_name, history_file in get_history_files().items():
    if channel_name not in channel_name_id: continue
    channel_id = channel_name_id[channel_name]
    with open(history_file, "r") as f:
        connection.executemany("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", message_values(f))

connection.commit()
connection.close()
