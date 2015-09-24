#!/usr/bin/env python3

import os, sys
import argparse
import json, time
from datetime import datetime

import recurrent

# process command line arguments
parser = argparse.ArgumentParser(description="Slice and filter Slack chat history")
parser.add_argument("--history", help="Directory to look for JSON chat history files in (e.g., \"~/.slack-history\")")
parser.add_argument("-f", "--filter-from", help="Show only messages at or after a date/time (e.g., \"4pm september 8 2015\")")
parser.add_argument("-t", "--filter-to", help="Show only messages before or at a date/time (e.g., \"8pm september 9 2015\")")
parser.add_argument("-c", "--filter-channel", action="append", help="Show only messages within a channel (e.g., \"general\", \"#general\")")
parser.add_argument("-u", "--filter-user", action="append", help="Show only messages by a specific user (e.g., \"@anthony\", \"anthony\", \"Anthony Zhang\")")
parser.add_argument("-i", "--filter-contains", action="append", help="Show only messages that contain a specified string (e.g., \"wing night\", \"nuggets\")")
parser.add_argument("-s", "--sort", choices=["time", "channel", "user", "text"], default="time", help="Show only messages that contain a specified string (e.g., \"wing night\", \"nuggets\")")
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

# process --filter-channel arguments
if args.filter_channel:
    channel_names = {entry["name"] for entry in CHANNELS}
    FILTER_CHANNELS = {channel.lstrip("#") for channel in args.filter_channel}
    for channel_name in FILTER_CHANNELS:
        if channel_name not in channel_names:
            print("Unknown channel \"{}\" specified via the --filter-channel flag.".format(channel_name), file=sys.stderr)
            sys.exit(1)
else:
    FILTER_CHANNELS = None

# process --filter-user arguments
if args.filter_user:
    user_ids_by_name = {}
    for entry in USERS:
        user_ids_by_name[entry["name"]] = entry["id"]
        if entry.get("real_name", "") != "":
            user_ids_by_name[entry["real_name"]] = entry["id"]
    FILTER_USERS = set()
    for user_name in args.filter_user:
        if user_name not in user_ids_by_name:
            print("Unknown user \"{}\" specified via the --filter-user flag.".format(channel_name), file=sys.stderr)
            sys.exit(1)
        FILTER_USERS.add(user_ids_by_name[user_name])
else:
    FILTER_USERS = None

# process --filter-contains arguments
FILTER_CONTAINS = args.filter_contains or []

# process --sort argument
SORT_BY = args.sort

# process all the messages
user_names_by_id = {entry["id"]: entry["name"] for entry in USERS}
result = []
for dirpath, _, filenames in os.walk(CHAT_HISTORY_DIRECTORY):
    for history_file in filenames:
        channel_name, extension = os.path.splitext(os.path.basename(history_file))
        if extension != ".json": continue
        if FILTER_CHANNELS is not None and channel_name not in FILTER_CHANNELS: continue
        with open(os.path.join(dirpath, history_file), "r") as f:
            for line in f.readlines():
                message = json.loads(line)
                if "user" not in message or "text" not in message: continue
                message_time = datetime.fromtimestamp(int(message["ts"].split(".")[0]))
                if FILTER_FROM is not None and message_time < FILTER_FROM: continue
                if FILTER_TO is not None and message_time > FILTER_TO: continue
                user_id, text = message["user"], message["text"]
                if FILTER_USERS is not None and user_id not in FILTER_USERS: continue
                if FILTER_CONTAINS is not None and not all(value in text for value in FILTER_CONTAINS): continue
                result.append((message_time, channel_name, user_names_by_id.get(user_id, user_id), text))
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
for entry in result:
    print(entry)
