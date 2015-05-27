#!/usr/bin/env python3

import time, json, sys
from datetime import datetime

from slackclient import SlackClient

from process_chat_message import process_chat_message

def log(value):
    print(datetime.now(), value, file=sys.stderr)
    sys.stderr.flush() # this is needed if redirecting to files

if len(sys.argv) != 2:
    log("Usage: {} SLACK_BOT_TOKEN".format(sys.argv[0]))
    sys.exit(1)

SLACK_TOKEN = sys.argv[1]

def download_file(name, url):
    import urllib.request, shutil, os
    path = os.path.join("files", name)
    os.makedirs(os.path.dirname(path))
    with urllib.request.urlopen(url) as response, open(path, "wb") as out_file:
        shutil.copyfileobj(response, out_file)

channel_id_map = {}
user_id_map = {}
def get_channel(client, channel_id):
    """Returns the name of the channel with the channel ID `channel_id`."""
    if channel_id not in channel_id_map:
        channel = json.loads(client.api_call("channels.info", channel=channel_id).decode("utf-8"))["channel"]
        channel_id_map[channel_id] = channel["name"]
    return channel_id_map[channel_id]
def get_channel_id_by_name(client, channel_name):
    """Returns the ID of the channel with name `channel_name`, or `None` if there are none."""
    if channel_name in channel_id_map.values():
        for channel_id, name in channel_id_map.items():
            if name == channel_name: return channel_id
    else:
        channels = json.loads(client.api_call("channels.list").decode("utf-8"))["channels"]
        for channel in channels:
            if channel["name"] == channel_name:
                channel_id_map[channel["id"]] = channel_name
                return channel["id"]
    return None
def get_user(client, user_id):
    """Returns the username of the user with user ID `user_id`."""
    if user_id not in user_id_map:
        user = json.loads(client.api_call("users.info", user=user_id).decode("utf-8"))["user"]
        user_id_map[user_id] = user["name"]
    return user_id_map[user_id]

def on_ignoreable_message(client, message): pass
def on_loggable_message(client, message):
    if "file" in message: download_file(message["file"]["id"] + " - " + message["file"]["name"], message["file"]["url_download"])
    if isinstance(message.get("channel"), str): message["channel"] = get_channel(client, message["channel"])
    if isinstance(message.get("user"), str): message["user"] = get_user(client, message["user"])
    if isinstance(message.get("inviter"), str): message["inviter"] = get_user(client, message["inviter"])
    print(json.dumps(message)); sys.stdout.flush() # log the message to stdout in JSON format
def on_channel_created_message(client, message):
    on_loggable_message(client, message)
    client.rtm_send_message(get_channel_id_by_name(client, "general"), "pls invit 2 #{}".format(message["channel"]["name"]))
def on_text_message(client, message):
    on_loggable_message(client, message)
    if "subtype" not in message and isinstance(message.get("user"), str) and isinstance(message.get("channel"), str) and isinstance(message.get("text"), str) and isinstance(message.get("ts"), str):
        process_chat_message(client, message["user"], get_channel_id_by_name(client, message["channel"]), message["text"], message["ts"])

message_actions = {
    "hello":                   on_ignoreable_message,
    "pong":                    on_ignoreable_message,
    "message":                 on_text_message,
    "user_typing":             on_ignoreable_message,
    "channel_marked":          on_ignoreable_message,
    "channel_created":         on_channel_created_message,
    "channel_joined":          on_loggable_message,
    "channel_left":            on_loggable_message,
    "channel_deleted":         on_loggable_message,
    "channel_rename":          on_loggable_message,
    "channel_archive":         on_loggable_message,
    "channel_unarchive":       on_loggable_message,
    "channel_history_changed": on_ignoreable_message,
    "im_created":              on_loggable_message,
    "im_open":                 on_loggable_message,
    "im_close":                on_loggable_message,
    "im_marked":               on_ignoreable_message,
    "im_history_changed":      on_ignoreable_message,
    "group_joined":            on_loggable_message,
    "group_left":              on_loggable_message,
    "group_open":              on_loggable_message,
    "group_close":             on_loggable_message,
    "group_archive":           on_loggable_message,
    "group_unarchive":         on_loggable_message,
    "group_rename":            on_loggable_message,
    "group_marked":            on_ignoreable_message,
    "group_history_changed":   on_ignoreable_message,
    "file_created":            on_loggable_message,
    "file_shared":             on_loggable_message,
    "file_unshared":           on_loggable_message,
    "file_public":             on_loggable_message,
    "file_private":            on_loggable_message,
    "file_change":             on_loggable_message,
    "file_deleted":            on_loggable_message,
    "file_comment_added":      on_loggable_message,
    "file_comment_edited":     on_loggable_message,
    "file_comment_deleted":    on_loggable_message,
    "pin_added":               on_loggable_message,
    "pin_removed":             on_loggable_message,
    "presence_change":         on_ignoreable_message,
    "manual_presence_change":  on_ignoreable_message,
    "pref_change":             on_ignoreable_message,
    "user_change":             on_ignoreable_message,
    "team_join":               on_loggable_message,
    "star_added":              on_loggable_message,
    "star_removed":            on_loggable_message,
    "emoji_changed":           on_ignoreable_message,
    "commands_changed":        on_ignoreable_message,
    "team_plan_change":        on_ignoreable_message,
    "team_pref_change":        on_ignoreable_message,
    "team_rename":             on_loggable_message,
    "team_domain_change":      on_loggable_message,
    "email_domain_changed":    on_loggable_message,
    "bot_added":               on_loggable_message,
    "bot_changed":             on_loggable_message,
    "accounts_changed":        on_ignoreable_message,
    "team_migration_started":  on_ignoreable_message,
}

def main():
    # connect to the Slack Realtime Messaging API
    log("[INFO] CONNECTING TO SLACK REALTIME MESSAGING API...")
    client = SlackClient(SLACK_TOKEN)
    if not client.rtm_connect(): raise ConnectionError("Could not connect to Slack Realtime Messaging API (possibly a bad token or network issue)")
    log("[INFO] CONNECTED TO SLACK REALTIME MESSAGING API")

    last_ping = time.time()
    while True:
        for message in client.rtm_read():
            if "type" in message:
                if message["type"] in message_actions:
                    try: message_actions[message["type"]](client, message)
                    except KeyboardInterrupt: raise
                    except Exception as e:
                        log("[ERROR] MESSAGE PROCESSING THREW EXCEPTION:")
                        import traceback; log(traceback.format_exc())
                        log("[ERROR] MESSAGE CONTENTS: {}".format(message))
                else:
                    log("[ERROR] UNKNOWN INCOMING MESSAGE FORMAT: {}".format(message))
        
        # ping the server periodically to make sure our connection is kept alive
        if time.time() - last_ping > 5:
            client.server.ping()
            last_ping = time.time()
        
        time.sleep(1) # 1 message per second is the upper limit for message sending before being disconnected

if __name__ == "__main__":
    while True:
        try: main() # start the main loop
        except KeyboardInterrupt: break
        except Exception as e:
            log("[ERROR] MAIN LOOP THREW EXCEPTION:")
            import traceback; log(traceback.format_exc())
            log("[INFO] RESTARTING IN 5 SECONDS...")
            time.sleep(5)
    log("[INFO] SHUTTING DOWN...")
