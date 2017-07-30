#!/usr/bin/env python3

import json, os, sys, logging, time
import urllib.request, shutil

from slackclient import SlackClient

if not 2 <= len(sys.argv) <= 3:
    print("Usage: {} SLACK_API_TOKEN [SAVE_FOLDER]".format(sys.argv[0]))
    print("    SLACK_API_TOKEN    Slack API token (obtainable from https://api.slack.com/tokens)".format(sys.argv[0]))
    print("    SAVE_FOLDER        Folder to save messages in (defaults to ./@history)".format(sys.argv[0]))
    sys.exit(1)

SLACK_TOKEN = sys.argv[1]
SAVE_FOLDER = sys.argv[2] if len(sys.argv) >= 3 else "@history"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def text_file_last_line(f, encoding="utf-8"):
    """Efficiently obtains the last line of a text file."""
    f.seek(0, os.SEEK_END) # start at the second to last character, since text files should end in a newline
    if f.tell() < 2: return ""
    f.seek(-2, os.SEEK_END) # start at the second to last character, since text files should end in a newline
    while f.read(1) != b"\n":
        if f.tell() < 2: # arrived at beginning of file, so there is only one line
            f.seek(0, os.SEEK_SET) # only one line; move to beginning so we read the whole line
            break
        f.seek(-2, os.SEEK_CUR) # go backward from the end of the file until we find a full line
    return f.readline().decode(encoding)

def download_metadata(slack_client, save_folder):
    meta_folder = os.path.join(save_folder, "metadata")
    os.makedirs(meta_folder, exist_ok=True)

    logging.info("DOWNLOADING CHANNEL INFORMATION...")
    channels_info = slack_client.api_call("channels.list")["channels"]
    with open(os.path.join(meta_folder, "channels.json"), "w") as f:
        json.dump(channels_info, f, sort_keys=True, indent=2)

    logging.info("DOWNLOADING USER INFORMATION...")
    users_info = slack_client.api_call("users.list")["members"]
    with open(os.path.join(meta_folder, "users.json"), "w") as f:
        json.dump(users_info, f, sort_keys=True, indent=2)

    return channels_info, users_info

def download_file(slack_token, save_folder, name, url):
    files_dir = os.path.join(save_folder, "files")
    file_path = os.path.join(files_dir, name)
    if os.path.dirname(os.path.normpath(file_path)) != files_dir: return # do not allow downloading to files not in the designated folder
    if os.path.exists(file_path): return # file was previously downloaded
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    request = urllib.request.Request(url, headers={"Authorization": "Bearer {}".format(slack_token)})
    with urllib.request.urlopen(request) as response:
        with open(file_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

def download_slack_history(slack_token, save_folder):
    client = SlackClient(slack_token)
    os.makedirs(save_folder, exist_ok=True)

    channels_info, users_info = download_metadata(client, save_folder)
    
    total_new_messages = 0
    channel_names = {entry["id"]: entry["name"] for entry in channels_info}
    for channel_id, channel_name in channel_names.items():
        message_file_path = os.path.join(save_folder, "{}.json".format(channel_id))
        
        # read the timestamp of the oldest message in the logs
        try:
            with open(message_file_path, "rb") as f:
                last_line = text_file_last_line(f)
                if last_line == "": raise FileNotFoundError # treat empty files as nonexistant
                existing_newest_message_time = float(json.loads(last_line)["ts"])
        except FileNotFoundError:
            existing_newest_message_time = float("-inf") # no oldest message, use default timestamp

        time.sleep(1)  # wait a bit to prevent us from getting rate limited
        logging.info("DOWNLOADING MESSAGES IN #{} (UNTIL TIMESTAMP {})".format(channel_name, existing_newest_message_time))
        response = client.api_call("channels.history", channel=channel_id, count=100)
        messages = response["messages"]
        oldest_message_timestamp = None
        while messages and response["has_more"]: # messages are retried from newest to oldest, but we'll reverse that later
            oldest_message_timestamp = float(messages[-1]["ts"])
            if oldest_message_timestamp <= existing_newest_message_time: break

            logging.info("DOWNLOADING MESSAGES STARTING FROM {} IN #{} (UNTIL TIMESTAMP {})".format(oldest_message_timestamp, channel_name, existing_newest_message_time))
            response = client.api_call("channels.history", channel=channel_id, count=100, latest=oldest_message_timestamp)
            messages += response["messages"]
        else: # we've reached the history limit, because we reached the end of messages without finding the last one from the previous run
            if oldest_message_timestamp is not None: # there was at least one chunk of messages
                oldest_message_timestamp = float(messages[-1]["ts"]) # recompute the timestamp of the most recent message from the previous run
                logging.warn("RAN OUT OF HISTORY AT TIMESTAMP {} BEFORE REACHING {} IN #{}".format(oldest_message_timestamp, existing_newest_message_time, channel_name))
        
        # remove any messages that duplicate those we've already downloaded in the past
        messages, i = list(reversed(messages)), 0
        while i < len(messages) and float(messages[i]["ts"]) <= existing_newest_message_time: i += 1
        messages = messages[i:]

        if messages:
            logging.info("DOWNLOADED {} NEW MESSAGES IN #{}".format(len(messages), channel_name))

        # download message files where applicable
        for message in messages:
            if "file" not in message: continue
            file_entry = message["file"]
            if "url_private_download" not in file_entry: continue # files like Google docs and such
            logging.info("DOWNLOADING FILE \"{}\" (ID {}) IN #{}".format(file_entry["name"], file_entry["id"], channel_name))
            try:
                download_file(slack_token, save_folder, "{} - {}".format(file_entry["id"], file_entry["name"]), file_entry["url_private_download"])
            except:
                logging.exception("FILE DOWNLOAD FAILED FOR {}".format(file_entry["url_private_download"]))
        
        with open(message_file_path, "a") as f:
            for message in messages:
                f.write(json.dumps(message, sort_keys=True) + "\n")
        
        total_new_messages += len(messages)
    logging.info("DOWNLOADED {} NEW MESSAGES IN ALL CHANNELS".format(total_new_messages))

def backfill_files():
    """Goes through all the referenced files in the history and attempt to download them if they aren't already downloaded."""
    def get_history_files():
        """Returns a mapping from channel IDs to absolute file paths of their history entries"""
        for dirpath, _, filenames in os.walk(save_folder):
            result = {}
            for history_file in filenames:
                channel_id, extension = os.path.splitext(os.path.basename(history_file))
                if extension != ".json": continue
                result[channel_id] = os.path.join(dirpath, history_file)
            return result
        return {}
    for channel_id, history_file in get_history_files().items():
        with open(history_file, "r") as f:
            for entry in f:
                message = json.loads(entry)
                if "file" not in message: continue
                file_entry = message["file"]
                try:
                    if "url_private_download" in file_entry:
                        download_file("{} - {}".format(file_entry["id"], file_entry["name"]), file_entry["url_private_download"])
                    elif "url_download" in file_entry:
                        download_file("{} - {}".format(file_entry["id"], file_entry["name"]), file_entry["url_download"])
                except:
                    logging.exception("FILE DOWNLOAD FAILED FOR {}".format(file_entry["url_private_download"]))

if __name__ == "__main__":
    download_slack_history(SLACK_TOKEN, SAVE_FOLDER)
    #backfill_files()
