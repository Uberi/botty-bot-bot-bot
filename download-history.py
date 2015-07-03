#!/usr/bin/env python3

import json, os, sys

from slackclient import SlackClient

if not 2 <= len(sys.argv) <= 3:
    print("Usage: {} SLACK_API_TOKEN [SAVE_FOLDER]".format(sys.argv[0]))
    print("    SLACK_API_TOKEN    Slack API token (obtainable from https://api.slack.com/tokens)".format(sys.argv[0]))
    print("    SAVE_FOLDER        Folder to save messages in (defaults to @history)".format(sys.argv[0]))
    sys.exit(1)

SLACK_TOKEN = sys.argv[1]
SAVE_FOLDER = sys.argv[2] if len(sys.argv) >= 3 else "@history"

def text_file_last_line(f, encoding="utf-8"):
    """Efficiently obtains the last line of a text file."""
    f.seek(0, os.SEEK_END) # start at the second to last character, since text files should end in a newline
    if f.tell() < 2: return ""
    f.seek(-2, os.SEEK_END) # start at the second to last character, since text files should end in a newline
    while f.read(1) != b"\n":
        if f.tell() < 2: # arrived at beginning of file, so there is only one line
            f.seek(0, os.SEEK_SET)
            break
        f.seek(-2, os.SEEK_CUR) # go backward from the end of the file until we find a full line
    return f.readline().decode(encoding)

def download_file(name, url):
    import urllib.request, shutil, os
    path = os.path.join(SAVE_FOLDER, "files", name)
    if os.path.exists(path): return # file was previously downloaded
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(url) as response, open(path, "wb") as out_file:
        shutil.copyfileobj(response, out_file)

def main():
    client = SlackClient(SLACK_TOKEN)
    os.makedirs(SAVE_FOLDER, exist_ok=True)
    
    # download channel and user metadata
    meta_folder = os.path.join(SAVE_FOLDER, "metadata")
    os.makedirs(meta_folder, exist_ok=True)
    print("DOWNLOADING CHANNEL INFORMATION...")
    response = json.loads(client.api_call("channels.list").decode("utf-8"))
    channels = {entry["name"]: entry["id"] for entry in response["channels"]}
    with open(os.path.join(meta_folder, "channels.json"), "w") as f: json.dump(response["channels"], f, sort_keys=True, indent=2)
    print("DOWNLOADING USER INFORMATION...")
    response = json.loads(client.api_call("users.list").decode("utf-8"))
    with open(os.path.join(meta_folder, "users.json"), "w") as f: json.dump(response["members"], f, sort_keys=True, indent=2)
    
    total_new_messages = 0
    for channel, channel_id in channels.items():
        message_file_path = os.path.join(SAVE_FOLDER, "{}.json".format(channel))
        
        # read the timestamp of the oldest message in the logs
        try:
            with open(message_file_path, "rb") as f:
                last_line = text_file_last_line(f)
                if last_line == "": raise FileNotFoundError # treat empty files as nonexistant
                existing_newest_message_time = float(json.loads(last_line)["ts"])
        except FileNotFoundError:
            existing_newest_message_time = 0 # no oldest message, use default timestamp
        
        print("DOWNLOADING MESSAGES IN #{} (UNTIL TIMESTAMP {})".format(channel, existing_newest_message_time))
        response = json.loads(client.api_call("channels.history", channel=channel_id, count=100).decode("utf-8"))
        messages = response["messages"]
        while response["has_more"]:
            oldest_message_timestamp = float(messages[-1]["ts"])
            if oldest_message_timestamp <= existing_newest_message_time: break
            
            print("DOWNLOADING MESSAGES STARTING FROM {} IN #{} (UNTIL TIMESTAMP {})".format(oldest_message_timestamp, channel, existing_newest_message_time))
            response = json.loads(client.api_call("channels.history", channel=channel_id, count=100, latest=oldest_message_timestamp).decode("utf-8"))
            messages += response["messages"]
        
        # sort messages from oldest to newest, and remove messages that are already stored
        messages, i = list(reversed(messages)), 0
        while i < len(messages) and float(messages[i]["ts"]) <= existing_newest_message_time: i += 1
        messages = messages[i:]
        
        print("DOWNLOADED {} NEW MESSAGES IN #{}".format(len(messages), channel))
        
        # download message files where applicable
        for message in messages:
            if "file" not in message: continue
            file_entry = message["file"]
            if "url_download" not in file_entry: continue # files like Google docs and such
            print("DOWNLOADING FILE \"{}\" (ID {}) IN #{}".format(file_entry["name"], file_entry["id"], channel))
            download_file("{} - {}".format(file_entry["id"], file_entry["name"]), file_entry["url_download"])
        
        with open(message_file_path, "a") as f:
            for message in messages:
                f.write(json.dumps(message, sort_keys=True) + "\n")
        
        total_new_messages += len(messages)
    print("DOWNLOADED {} NEW MESSAGES IN ALL CHANNELS".format(total_new_messages))

if __name__ == "__main__": main()
