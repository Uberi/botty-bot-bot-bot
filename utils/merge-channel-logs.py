#!/usr/bin/env python3

import sys
import json

if len(sys.argv) < 2:
    print("Usage: {} HISTORY_FILE_1 [...] HISTORY_FILE_N > MERGED_HISTORY_FILE".format(sys.argv[0]))
    print()
    print("Reads one or more history files, adds them together, deduplicates, checks for errors, and outputs a combined history file.")
    print("Mainly used in case we need to reconstruct a log from multiple partial logs.")
    print("According to https://github.com/slackhq/slack-api-docs/issues/7, timestamp values are unique within a given channel.")
    print("Therefore, this program should only be used for log files for a single channel.")
    print("WARNING: do not redirect the output of this program into any of the input files! Results are undefined.")
    sys.exit(1)
history_files = sys.argv[1:]

def resolve_conflicting_messages(message_1, message_2):
    """Returns a message that seems to have been retrieved more recently out of `message_1` and `message_2`, or `None` if they seem to conflict."""
    message_1, message_2 = message_1.copy(), message_2.copy()
    edited_1, edited_2 = message_1.pop("edited", None), message_2.pop("edited", None)
    replies_1, replies_2 = message_1.pop("replies", []), message_2.pop("replies", [])
    pinned_to_1, pinned_to_2 = message_1.pop("pinned_to", None), message_2.pop("pinned_to", None)
    reactions_1 , reactions_2 = message_1.pop("reactions", []), message_2.pop("reactions", [])
    message_1.pop("thread_ts", None), message_2.pop("thread_ts", None)
    message_1.pop("last_read", None), message_2.pop("last_read", None)
    message_1.pop("subscribed", None), message_2.pop("subscribed", None)
    message_1.pop("reply_count", None), message_2.pop("reply_count", None)
    message_1.pop("unread_count", None), message_2.pop("unread_count", None)
    message_1.pop("attachments", None), message_2.pop("attachments", None)
    message_1.pop("file", None), message_2.pop("file", None)

    # ignore changed text if one of the messages was edited
    if edited_1 or edited_2:
        message_1.pop("text", None), message_2.pop("text", None)

    if message_1 != message_2: return None # no solution to conflicts found
    if edited_1 and not edited_2: return message_1 # message 1 was edited, so it's definitely newer
    if not edited_1 and edited_2: return message_2 # message 2 was edited, so it's definitely newer
    if len(replies_1) > len(replies_2): return message_1 # more replies to message 1, it's probably newer
    if len(replies_1) < len(replies_2): return message_2 # more replies to message 2, it's probably newer
    if pinned_to_1 and not pinned_to_2: return message_1 # message 1 was pinned, so it's probably newer
    if not pinned_to_1 and pinned_to_2: return message_2 # message 2 was pinned, so it's probably newer
    if sum(entry["count"] for entry in reactions_1) > sum(entry["count"] for entry in reactions_2): return message_1 # more reactions to message 1, it's probably newer
    if sum(entry["count"] for entry in reactions_1) < sum(entry["count"] for entry in reactions_2): return message_2 # more reactions to message 2, it's probably newer
    return message_1 # default to message 1

combined_log = {}
for history_file in history_files:
    with open(history_file, "r") as history:
        for line in history:
            message = json.loads(line)
            timestamp = message["ts"]
            other_message = combined_log.get(timestamp)
            if other_message is None:
                combined_log[timestamp] = message
            else:
                resolved_message = resolve_conflicting_messages(message, other_message)
                if resolved_message is None:
                    print("============ CONFLICT FOUND ============", file=sys.stderr)
                    print("MESSAGE 1:", file=sys.stderr)
                    print(message, file=sys.stderr)
                    print("MESSAGE 2:", file=sys.stderr)
                    print(other_message, file=sys.stderr)
                else:
                    combined_log[timestamp] = resolved_message
for timestamp in sorted(combined_log, key=lambda ts: (int(ts.split(".")[0]), ts.split(".")[1])):
    print(json.dumps(combined_log[timestamp], sort_keys=True))