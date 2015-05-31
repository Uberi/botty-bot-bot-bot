#!/usr/bin/env python3

import time, json, sys
from datetime import datetime

from slackclient import SlackClient

from process_chat_message import process_text_message

def log(value):
    print(datetime.now(), value, file=sys.stderr)
    sys.stderr.flush() # this is needed if redirecting to files

if len(sys.argv) != 2:
    log("Usage: {} SLACK_BOT_TOKEN".format(sys.argv[0]))
    sys.exit(1)
SLACK_TOKEN = sys.argv[1]

def on_message(client, message):
    if message.get("type") == "message":
        if isinstance(message.get("user"), str) and isinstance(message.get("channel"), str) and isinstance(message.get("text"), str) and isinstance(message.get("ts"), str):
            process_text_message(client, message["user"], message["channel"], message["text"], message["ts"])

def main():
    # connect to the Slack Realtime Messaging API
    log("[INFO] CONNECTING TO SLACK REALTIME MESSAGING API...")
    client = SlackClient(SLACK_TOKEN)
    if not client.rtm_connect(): raise ConnectionError("Could not connect to Slack Realtime Messaging API (possibly a bad token or network issue)")
    log("[INFO] CONNECTED TO SLACK REALTIME MESSAGING API")

    last_ping = time.time()
    while True:
        for message in client.rtm_read():
            try: on_message(client, message)
            except KeyboardInterrupt: raise
            except Exception:
                log("[ERROR] MESSAGE PROCESSING THREW EXCEPTION:")
                import traceback; log(traceback.format_exc())
                log("[ERROR] MESSAGE CONTENTS: {}".format(message))

        # ping the server periodically to make sure our connection is kept alive
        if time.time() - last_ping > 5:
            client.server.ping()
            last_ping = time.time()
        
        time.sleep(1) # 1 message per second is the upper limit for message sending before being disconnected

if __name__ == "__main__":
    while True:
        try: main() # start the main loop
        except KeyboardInterrupt: break
        except Exception:
            log("[ERROR] MAIN LOOP THREW EXCEPTION:")
            import traceback; log(traceback.format_exc())
            log("[INFO] RESTARTING IN 5 SECONDS...")
            time.sleep(5)
    log("[INFO] SHUTTING DOWN...")
