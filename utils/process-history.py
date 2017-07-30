#!/usr/bin/env python3

import os, sys, re
import argparse
import json, time
from datetime import datetime
from collections import deque

import recurrent

# process command line arguments
parser = argparse.ArgumentParser(description="Slice and filter Slack chat history.")
parser.add_argument("--history", help="Directory to look for JSON chat history files in (e.g., \"~/.slack-history\").")
parser.add_argument("-f", "--filter-from", help="Show only messages at or after a date/time (e.g., \"4pm september 8 2015\").")
parser.add_argument("-t", "--filter-to", help="Show only messages before or at a date/time (e.g., \"8pm september 9 2015\").")
parser.add_argument("-c", "--filter-channel", help="Show only messages within channels with names matching a specific regular expression (e.g., \"general\", \"general|random\").")
parser.add_argument("-u", "--filter-user", help="Show only messages by users with usernames or real names matching a specific regular expression (e.g., \"anthony\", \"[AO]nthon[yo] Zh[ao]ng\").")
parser.add_argument("-i", "--filter-text", help="Show only messages with text matching a specified regular expression (e.g., \"wings?\", \"chicken\\s+nuggets\").")
parser.add_argument("-s", "--sort", choices=["time", "channel", "user", "text"], default="time", help="Sort the resulting messages by the specified criteria.")
parser.add_argument("-r", "--context", type=int, default=0, help="Show a specified number of surrounding messages around the channel in each matched message.")
parser.add_argument("-o", "--output", default="{timestamp} {channel:>15} {marker} {user}: {text}", help="Show output using the specified Python format string (e.g., \"{user}: {text}\").")
args = parser.parse_args()

# process --history argument
if args.history:
    CHAT_HISTORY_DIRECTORY = args.history
else:
    CHAT_HISTORY_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "@history")
if not os.path.exists(CHAT_HISTORY_DIRECTORY):
    print("Non-existant path specified via the --history flag.", file=sys.stderr)
    sys.exit(1)
if not os.path.isdir(CHAT_HISTORY_DIRECTORY):
    print("Non-directory specified via the --history flag.", file=sys.stderr)
    sys.exit(1)

# process --filter-from argument
if args.filter_from:
    r = recurrent.RecurringEvent()
    FILTER_FROM = r.parse(args.filter_from)
    if not isinstance(FILTER_FROM, datetime):
        print("Unknown date/time specified via the --filter-from flag.", file=sys.stderr)
        sys.exit(1)
else:
    FILTER_FROM = None

# process --filter-to argument
if args.filter_to:
    r = recurrent.RecurringEvent()
    FILTER_TO = r.parse(args.filter_to)
    if not isinstance(FILTER_TO, datetime):
        print("Unknown date/time specified via the --filter-to flag.", file=sys.stderr)
        sys.exit(1)
else:
    FILTER_TO = None

FILTER_CHANNEL = re.compile(args.filter_channel) if args.filter_channel else None # process --filter-channel argument
FILTER_USER = re.compile(args.filter_user) if args.filter_user else None # process --filter-user argument
FILTER_TEXT = re.compile(args.filter_text) if args.filter_text else None # process --filter-text arguments
SORT_BY = args.sort # process --sort argument
CONTEXT = args.context # process --context argument
OUTPUT = args.output # process --output argument

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

# process all the messages
previous_messages = deque(maxlen=CONTEXT)
context_after = 0
result = []
for dirpath, _, filenames in os.walk(CHAT_HISTORY_DIRECTORY):
    for history_file in filenames:
        channel_id, extension = os.path.splitext(os.path.basename(history_file))
        channel_name = CHANNEL_NAMES_BY_ID[channel_id]
        if extension != ".json": continue
        if FILTER_CHANNEL and not FILTER_CHANNEL.search(channel_name): continue
        with open(os.path.join(dirpath, history_file), "r") as f:
            for line in f.readlines():
                message = json.loads(line)
                if "user" not in message or "text" not in message: continue
                user_id, text = message["user"], server_text_to_text(message["text"])
                user_name = USER_NAMES_BY_ID.get(user_id, user_id)
                user_real_name = USER_REAL_NAMES_BY_ID.get(user_id, "")

                message_time = datetime.fromtimestamp(int(message["ts"].split(".")[0]))
                if (
                    (FILTER_FROM is None or message_time >= FILTER_FROM) and
                    (FILTER_TO is None or message_time <= FILTER_TO) and
                    (FILTER_USER is None or FILTER_USER.search(user_name) or FILTER_USER.search(user_real_name)) and
                    (FILTER_TEXT is None or FILTER_TEXT.search(text))
                ): # matched message
                    result += previous_messages
                    previous_messages.clear()
                    result.append((message_time, channel_name, user_name, text, False))
                    context_after = CONTEXT
                else: # non-matched message
                    previous_messages.append((message_time, channel_name, user_name, text, True))
                    if context_after > 0: # in context following a match
                        context_after -= 1
                        result.append((message_time, channel_name, user_name, text, True))
                        previous_messages.clear() # prevent next match from duplicating context
    break # stop processing after we walk the root directory

# apply sorting
if SORT_BY == "time":
    result = sorted(result, key=lambda x: x[0])
elif SORT_BY == "channel":
    result = sorted(result, key=lambda x: x[1])
elif SORT_BY == "user":
    result = sorted(result, key=lambda x: x[2])
elif SORT_BY == "text":
    result = sorted(result, key=lambda x: x[3])

# print out the results
for (message_time, channel_name, user_name, text, is_context) in result:
    print(OUTPUT.format(timestamp=message_time, channel="#" + channel_name, marker="   " if is_context else ">>>", user=user_name, text=text))