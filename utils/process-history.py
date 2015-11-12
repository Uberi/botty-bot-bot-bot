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

# load metadata
with open(os.path.join(CHAT_HISTORY_DIRECTORY, "metadata", "channels.json")) as f:
    CHANNELS = json.load(f)
with open(os.path.join(CHAT_HISTORY_DIRECTORY, "metadata", "users.json")) as f:
    USERS = json.load(f)

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

# process all the messages
user_names_by_id = {entry["id"]: entry["name"] for entry in USERS}
user_real_names_by_id = {entry["id"]: entry["real_name"] for entry in USERS if "real_name" in entry}
previous_messages = deque(maxlen=CONTEXT)
context_after = 0
result = []
for dirpath, _, filenames in os.walk(CHAT_HISTORY_DIRECTORY):
    for history_file in filenames:
        channel_name, extension = os.path.splitext(os.path.basename(history_file))
        if extension != ".json": continue
        if FILTER_CHANNEL and not FILTER_CHANNEL.search(channel_name): continue
        with open(os.path.join(dirpath, history_file), "r") as f:
            for line in f.readlines():
                message = json.loads(line)
                if "user" not in message or "text" not in message: continue
                user_id, text = message["user"], message["text"]
                user_name = user_names_by_id.get(user_id, user_id)
                user_real_name = user_real_names_by_id.get(user_id, "")

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
    break

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
    print("{} {:>15} {} {}: {}".format(message_time, "#" + channel_name, "   " if is_context else ">>>", user_name, text))
