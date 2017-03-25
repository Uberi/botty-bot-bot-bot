#!/usr/bin/env python3

import time, json, sys, re, os, shutil, bluetooth
from datetime import datetime
import traceback
import logging
from collections import deque
from functools import lru_cache
from gtts import gTTS
from pygame import mixer

from slackclient import SlackClient

class SlackBot:
    """
    Slack bot base class. Includes lots of useful functionality that bots often require, such as messaging, connection management, and interfacing with APIs.

    This class is compatible with the [January 2017 release of the Slack API](https://api.slack.com/changelog).

    This class is intended to be subclassed, with the `on_step` and `on_message` methods overridden to do more useful things.
    """
    def __init__(self, token, logger=None):
        assert isinstance(token, str), "`token` must be a valid Slack API token"
        assert logger is None or not isinstance(logger, logging.Logger), "`logger` must be `None` or a logging function"

        self.client = SlackClient(token)
        if logger is None: self.logger = logging.getLogger(self.__class__.__name__)
        else: self.logger = logger

        # cached versions of methods
        self.get_user_info_by_id_cached = lru_cache(maxsize=256)(self.get_user_info_by_id)

        # incoming message fields
        self.unprocessed_incoming_messages = deque() # store unprocessed messages to allow message peeking

        # outgoing message fields
        self.max_message_id = 1 # every message sent over RTM needs a unique positive integer ID - this should technically be handled by the Slack library, but that's broken as of now
        self.last_say_time = 0 # store last message send timestamp to rate limit sending
        self.bot_user_id = None # ID of this bot user

    def on_step(self):
        self.logger.info("step handler called")
    def on_message(self, message_dict):
        self.logger.info("message handler called with message {}".format(message_dict))

    def start_loop(self):
        while True:
            try: self.start() # start the main loop
            except KeyboardInterrupt: break
            except Exception:
                self.logger.error("main loop threw exception:\n{}".format(traceback.format_exc()))
                self.logger.info("restarting in 5 seconds...")
                time.sleep(5)
        self.logger.info("shutting down...")

    def retrieve_unprocessed_incoming_messages(self):
        result = list(self.unprocessed_incoming_messages) + self.client.rtm_read()
        self.unprocessed_incoming_messages.clear()
        return result

    def peek_unprocessed_incoming_messages(self):
        self.unprocessed_incoming_messages.extend(self.client.rtm_read())
        return list(self.unprocessed_incoming_messages)

    def peek_new_messages(self):
        new_messages = self.client.rtm_read()
        self.unprocessed_incoming_messages.extend(new_messages)
        return list(new_messages)

    def start(self):
        # connect to the Slack Realtime Messaging API
        self.logger.info("connecting to Slack realtime messaging API...")
        if not self.client.rtm_connect(): raise ConnectionError("Could not connect to Slack realtime messaging API (possibly a bad token or network issue)")
        self.logger.info("connected to Slack realtime messaging API")

        # obtain the bot credentials
        authentication = self.client.api_call("auth.test")
        assert authentication["ok"], "Could not authenticate with Slack API"
        self.bot_user_id = authentication["user_id"]

        last_ping = time.monotonic()
        while True:
            # call all the step callbacks
            try: self.on_step()
            except Exception:
                self.logger.error("step processing threw exception:\n{}".format(traceback.format_exc()))

            # call all the message callbacks for each newly received message
            for message_dict in self.retrieve_unprocessed_incoming_messages():
                try: self.on_message(message_dict)
                except KeyboardInterrupt: raise
                except Exception:
                    self.logger.error("message processing threw exception:\n{}\n\nmessage contents:\n{}".format(traceback.format_exc(), message_dict))

            # ping the server periodically to make sure our connection is kept alive
            if time.monotonic() - last_ping > 5:
                self.client.server.ping()
                last_ping = time.monotonic()

            # delay to avoid checking the socket too often
            time.sleep(0.01)

    def say(self, sendable_text, *, channel_id, thread_id = None):
        """Say `sendable_text` in the channel with ID `channel_id`, returning the message ID (unique within each `SlackBot` instance)."""
        assert self.get_channel_name_by_id(channel_id) is not None, "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        assert isinstance(thread_id, str) or thread_id is None, "`thread_id` must be a valid Slack timestamp or None, rather than \"{}\"".format(thread_id)
        assert isinstance(sendable_text, str), "`text` must be a string rather than \"{}\"".format(sendable_text)

        # rate limit sending to 1 per second, since that's the Slack API limit
        current_time = time.monotonic()
        if current_time - self.last_say_time < 1:
            time.sleep(max(0, 1 - (current_time - self.last_say_time)))
            self.last_say_time += 1
        else:
            self.last_say_time = current_time

        self.logger.info("sending message to channel {}: {}".format(self.get_channel_name_by_id(channel_id), sendable_text))

        # the correct method to use here is `rtm_send_message`, but it's technically broken since it doesn't send the message ID so we're going to do this properly ourselves
        # the message ID allows us to correlate messages with message responses, letting us ensure that messages are actually delivered properly
        # see the "Sending messages" heading at https://api.slack.com/rtm for more details
        message_id = self.max_message_id
        self.max_message_id += 1
        if thread_id is not None: # message in a thread
            self.client.server.send_to_websocket({
                "id": message_id,
                "type": "message",
                "channel": channel_id,
                "text": sendable_text,
                "thread_ts": thread_id,
            })
        else: # top-level message
            self.client.server.send_to_websocket({
                "id": message_id,
                "type": "message",
                "channel": channel_id,
                "text": sendable_text,
            })
        return message_id

    def say_complete(self, sendable_text, *, channel_id, thread_id = None, timeout = 5):
        """Say `sendable_text` in the channel with ID `channel_id`, waiting for the message to finish sending (raising a `TimeoutError` if this takes more than `timeout` seconds), returning the message timestamp."""
        assert float(timeout) > 0, "`timeout` must be a positive number rather than \"{}\"".format(timeout)
        message_id = self.say(sendable_text, channel_id=channel_id, thread_id=thread_id)
        message_timestamp = None
        start_time = time.monotonic()
        while message_timestamp is None and time.monotonic() - start_time < timeout:
            # peek at new messages to see if the response is written
            for message_dict in self.peek_new_messages():
                if "ok" in message_dict and message_dict.get("reply_to") == message_id: # received reply for the sent message
                    if not message_dict["ok"]: raise ValueError("Message sending error: {}".format(message_dict.get("error", {}).get("msg")))
                    assert isinstance(message_dict.get("ts"), str), "Invalid message timestamp: {}".format(message_dict.get("ts"))
                    message_timestamp = message_dict["ts"]
                    break
            else:
                time.sleep(0.01)
        if message_timestamp is None: raise TimeoutError("Message sending timed out")
        return message_timestamp

    def react(self, channel_id, timestamp, emoticon):
        """React with `emoticon` to the message with timestamp `timestamp` in channel with ID `channel_id`."""
        assert self.get_channel_name_by_id(channel_id) is not None, "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        assert isinstance(timestamp, str), "`timestamp` must be a string rather than \"{}\"".format(timestamp)
        assert isinstance(emoticon, str), "`emoticon` must be a string rather than \"{}\"".format(emoticon)
        emoticon = emoticon.strip(":")
        self.logger.info("adding reaction :{}: to message with timestamp {} in channel {}".format(emoticon, timestamp, self.get_channel_name_by_id(channel_id)))
        response = self.client.api_call("reactions.add", name=emoticon, channel=channel_id, timestamp=timestamp)
        assert response.get("ok"), "Reaction addition failed: error {}".format(response.get("error"))

    def unreact(self, channel_id, timestamp, emoticon):
        """React with `emoticon` to the message with timestamp `timestamp` in channel with ID `channel_id`."""
        assert self.get_channel_name_by_id(channel_id) is not None, "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        assert isinstance(timestamp, str), "`timestamp` must be a string rather than \"{}\"".format(sendable_text)
        assert isinstance(emoticon, str), "`emoticon` must be a string rather than \"{}\"".format(sendable_text)
        emoticon = emoticon.strip(":")
        self.logger.info("removing reaction :{}: to message with timestamp {} in channel {}".format(emoticon, timestamp, self.get_channel_name_by_id(channel_id)))
        response = self.client.api_call("reactions.remove", name=emoticon, channel=channel_id, timestamp=timestamp)
        assert response.get("ok"), "Reaction removal failed: error {}".format(response.get("error"))

    def get_channel_name_by_id(self, channel_id):
        """Returns the name of the channel with ID `channel_id`, or `None` if there are no channels with that ID. Channels include public channels, direct messages with other users, and private groups."""
        assert isinstance(channel_id, str), "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        for entry in self.client.server.channels:
            if entry.id == channel_id: return entry.name
        return None

    def get_channel_id_by_name(self, channel_name):
        """Returns the ID of the channel with name `channel_name`, or `None` if there are no channels with that name. Channels include public channels, direct messages with other users, and private groups."""
        assert isinstance(channel_name, str), "`channel_name` must be a valid channel name rather than \"{}\"".format(channel_name)

        channel_name = channel_name.strip().lstrip("#")

        # check for channel reference (these are formatted like `<#CHANNEL_ID>` or `<#CHANNEL_ID|CHANNEL_NAME>`)
        match = re.match(r"<#(\w+)(?:\|[^>]+)?>$", channel_name)
        if match: return match.group(1)

        # search by channel name
        for entry in self.client.server.channels:
            if entry.name == channel_name: return entry.id

        return None

    def get_user_name_by_id(self, user_id):
        """Returns the username of the user with ID `user_id`, or `None` if there are no users with that ID."""
        assert isinstance(user_id, str), "`user_id` must be a valid user ID rather than \"{}\"".format(user_id)
        for key, entry in self.client.server.users.items():
            if entry.id == user_id: return entry.name
        return None

    def get_user_id_by_name(self, user_name):
        """Returns the ID of the user with username `user_name`, or `None` if there are no users with that username."""
        assert isinstance(user_name, str), "`user_name` must be a valid username rather than \"{}\"".format(user_name)

        user_name = user_name.strip().lstrip("@")

        # check for user reference (these are formatted like `<@USER_ID>` or `<@USER_ID|USER_NAME>`)
        match = re.match(r"^<@(\w+)(?:\|[^>]+)?>$", user_name)
        if match: return match.group(1)

        # search by user name
        for key, entry in self.client.server.users.items():
            if entry.name == user_name: return entry.id

        # search by user real name
        for key, entry in self.client.server.users.items():
            if entry.real_name == user_name: return entry.id

        return None

    def get_direct_message_channel_id_by_user_id(self, user_id):
        """Returns the channel ID of the direct message with the user with ID `user_id`, or `None` if the ID is invalid."""
        listing = self.client.api_call("im.list")["ims"]
        for entry in listing:
            if entry["user"] == user_id: return entry["id"]
        return None

    def get_user_info_by_id(self, user_id):
        """Returns a [metadata dictionary](https://api.slack.com/types/user) about the user with ID `user_id`."""
        assert self.get_user_name_by_id(user_id) is not None, "`user_id` must exist and be a valid user ID rather than \"{}\"".format(user_id)
        self.logger.info("retrieving user info for user {}".format(self.get_user_name_by_id(user_id)))
        response = self.client.api_call("users.info", user=user_id)
        assert response.get("ok"), "User info request failed: error {}".format(response.get("error"))
        assert isinstance(response.get("user"), dict) and "id" in response["user"], "User info response malformed: {}".format(response.get("user"))
        return response["user"]

    def get_user_is_bot(self, user_id):
        """Returns `True` if the user with ID `user_id` is a bot user, `False` otherwise."""
        if user_id == "USLACKBOT": return True # for some reason, Slack doesn't consider Slackbot a real bot
        user_info = self.get_user_info_by_id_cached(user_id)
        return user_info.get("is_bot", False)

    def server_text_to_sendable_text(self, server_text):
        """Returns `server_text`, a string in Slack server message format, converted into a string in Slack sendable message format."""
        assert isinstance(server_text, str), "`server_text` must be a string rather than \"{}\"".format(server_text)
        text_without_special_sequences = re.sub(r"<[^<>]*>", "", server_text)
        assert "<" not in text_without_special_sequences and ">" not in text_without_special_sequences, "Invalid special sequence in server text \"{}\", perhaps some text needs to be escaped"

        # process link references
        def process_special_sequence(match):
            original, body = match.group(0), match.group(1).split("|")[0]
            if body.startswith("#"): return original # channel reference, should send unchanged
            if body.startswith("@"): return original # user reference, should send unchanged
            if body.startswith("!"): return original # special command, should send unchanged
            return body # link, should remove angle brackets and label in order to allow it to linkify
        return re.sub(r"<(.*?)>", process_special_sequence, server_text)

    def text_to_sendable_text(self, text):
        """Returns `text`, a plain text string, converted into a string in Slack sendable message format."""
        assert isinstance(text, str), "`text` must be a string rather than \"{}\"".format(text)
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def sendable_text_to_text(self, sendable_text):
        """Returns `sendable_text`, a string in Slack sendable message format, converted into a plain text string. The transformation can lose some information for escape sequences, such as link labels."""
        assert isinstance(sendable_text, str), "`sendable_text` must be a string rather than \"{}\"".format(sendable_text)
        text_without_special_sequences = re.sub(r"<[^<>]*>", "", sendable_text)
        assert "<" not in text_without_special_sequences and ">" not in text_without_special_sequences, "Invalid special sequence in sendable text \"{}\", perhaps some text needs to be escaped"

        # process link references
        def process_special_sequence(match):
            original, body = match.group(0), match.group(1).split("|")[0]
            if body.startswith("#"): # channel reference
                channel_name = self.get_channel_name_by_id(body[1:])
                if channel_name is None: return original
                return "#" + channel_name
            if body.startswith("@"): # user reference
                user_name = self.get_user_name_by_id(body[1:])
                if user_name is None: return original
                return "@" + user_name
            if body.startswith("!"): # special command
                if body == "!channel": return "@channel"
                if body == "!group": return "@group"
                if body == "!everyone": return "@everyone"
            return original
        raw_text = re.sub(r"<(.*?)>", process_special_sequence, sendable_text)

        return raw_text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

    def administrator_console(self, namespace):
        """Start an interactive administrator Python console with namespace `namespace`."""
        import threading
        import readline # this makes arrow keys work for input()
        import code
        def start_console():
            code.interact(
                "##########################################\n" +
                "#   Botty Administrator Python Console   #\n" +
                "##########################################\n",
                local=namespace
            )
        console_thread = threading.Thread(target=start_console, daemon=True) # thread dies when main thread (the only non-daemon thread) exits
        console_thread.start()

class SlackDebugBot(SlackBot):
    """
    Slack debug bot - when started, exposes a command line interface for testing and debugging your Slack bot.

    This class is designed to emulate the functionality of the `SlackBot` class as closely as possible. For method documentation, refer to the corresponding methods in the `SlackBot` class.
    """
    def __init__(self, token, logger=None):
        assert isinstance(token, str), "`token` must be a valid Slack API token"
        assert logger is None or not isinstance(logger, logging.Logger), "`logger` must be `None` or a logging function"

        if logger is None: self.logger = logging.getLogger(self.__class__.__name__)
        else: self.logger = logger

        self.messages = []

        self.max_message_id = 1
        self.channel_name = "general"
        self.bot_user_id = "botty"

    def start_loop(self): self.start()

    def start(self):
        import threading, queue
        import readline # this makes arrow keys work for input()

        print("##########################################")
        print("#   Botty Slack Simulation Environment   #")
        print("##########################################")
        print()
        print("This is a local chat containing only you and Botty. It's useful for testing and debugging.")
        print()
        print("The following slash commands are available:")
        print()
        print("    /react -3 eggplant        | reacts to the third most recent text message with an eggplant")
        print("    /unreact 1 heart          | removes the heart reaction from the second earliest text message")
        print("    /reply -1 yeah definitely | replies to the most recent text message with \"yeah definitely\"")
        print("    /channel random           | moves you and Botty to the #random channel")
        print()

        user_input_queue = queue.Queue()
        def accept_input():
            while True:
                try:
                    text = input("\r\033[K" + "#{:<11}| Me: ".format(self.channel_name)) # clear the current line using Erase in Line ANSI escape code (this allows us to overwrite the existing prompt if present)
                except EOFError:
                    user_input_queue.put(None)
                    return

                user_input_queue.put(text)
                user_input_queue.join() # wait for the task to finish processing before allowing input again
        input_thread = threading.Thread(target=accept_input, daemon=True) # thread dies when main thread (the only non-daemon thread) exits
        input_thread.start()

        try:
            while True:
                self.on_step()
                while not user_input_queue.empty():
                    user_input = user_input_queue.get()
                    if user_input is None: raise KeyboardInterrupt # end of user input
                    self.handle_user_input(user_input)
                    user_input_queue.task_done()
                time.sleep(0.01)
        except KeyboardInterrupt: pass

    def handle_user_input(self, text):
        # handle `/react OFFSET EMOTICON` and `/unreact OFFSET EMOTICON` commands
        match_react = re.match(r"/react\s+(-?\d+)\s+(\S+)$", text)
        match_unreact = re.match(r"/unreact\s+(-?\d+)\s+(\S+)$", text)
        match = match_react or match_unreact
        if match:
            offset, emoticon = int(match.group(1)), match.group(2)
            try:
                target_message = self.messages[offset]
            except IndexError:
                print("[ERROR] Message offset {} is out of range".format(offset))
                return
            print("#{:<11}| You {} to \"{}\" with :{}:".format(self.channel_name, "reacted" if match_react else "unreacted", target_message["text"], emoticon))
            self.on_message({
                "type": "reaction_added" if match_react else "reaction_removed",
                "user": "UMe",
                "reaction": emoticon,
                "item": {"type": "message", "channel": "C" + self.channel_name, "ts": target_message["ts"]},
            })
            return

        # handle `/reply OFFSET MESSAGE` command
        match = re.match(r"/reply\s+(-?\d+)\s+(.*)$", text)
        if match:
            offset, body = int(match.group(1)), match.group(2)
            try:
                thread_first_message = self.messages[offset]
            except IndexError:
                print("[ERROR] Message offset {} is out of range".format(offset))
                return
            if "thread_ts" in thread_first_message:
                thread_id = thread_first_message["thread_ts"]
                thread_first_message = next((m for m in self.messages if m["ts"] == thread_id), None)
                assert thread_first_message is not None, "Invalid thread ID - can't find message with timestamp \"{}\"".format(thread_id)
            print("#{:<11}| Me (in thread for \"{}\"): {}".format(self.channel_name, thread_first_message["text"], body)) # clear the current line using Erase in Line ANSI escape code
            message = {
                "type": "message",
                "channel": "C" + self.channel_name,
                "user": "UMe",
                "text": self.text_to_sendable_text(body),
                "ts": str(time.monotonic()),
                "thread_ts": thread_first_message["ts"],
            }
            self.messages.append(message)
            self.on_message(message)
            return

        # handle `/channel CHANNEL_NAME` command
        match = re.match(r"/channel\s+(\w+)$", text)
        if match:
            self.channel_name = match.group(1)
            return

        # handle normal message
        message = {
            "type": "message",
            "channel": "C" + self.channel_name,
            "user": "UMe",
            "text": self.text_to_sendable_text(text),
            "ts": str(time.monotonic()),
        }
        self.messages.append(message)
        self.on_message(message)

    def say(self, sendable_text, *, channel_id, thread_id = None):
        assert self.get_channel_name_by_id(channel_id) is not None, "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        assert isinstance(thread_id, str) or thread_id is None, "`thread_id` must be a valid Slack timestamp or None, rather than \"{}\"".format(thread_id)
        assert isinstance(sendable_text, str), "`sendable_text` must be a string rather than \"{}\"".format(sendable_text)

        if thread_id is not None: # message in a thread
            thread_first_message = next((m for m in self.messages if m["ts"] == thread_id), None)
            assert thread_first_message is not None, "Invalid thread ID - can't find message with timestamp \"{}\"".format(thread_id)

            self.logger.info("sending message to channel {} (in thread {}): {}".format(self.get_channel_name_by_id(channel_id), thread_id, sendable_text))
            print("\r\033[K" + "#{:<11}| Botty (in thread for \"{}\"): {}".format(self.get_channel_name_by_id(channel_id), thread_first_message["text"], sendable_text)) # clear the current line using Erase in Line ANSI escape code
            self.messages.append({
                "type": "message",
                "channel": "C" + self.channel_name,
                "user": "UBotty",
                "text": sendable_text,
                "ts": str(time.monotonic()),
                "thread_ts": thread_id,
            })
        else: # top-level message
            self.logger.info("sending message to channel {}: {}".format(self.get_channel_name_by_id(channel_id), sendable_text))
            print("\r\033[K" + "#{:<11}| Botty: {}".format(self.get_channel_name_by_id(channel_id), sendable_text)) # clear the current line using Erase in Line ANSI escape code
            self.messages.append({
                "type": "message",
                "channel": "C" + self.channel_name,
                "user": "UBotty",
                "text": sendable_text,
                "ts": str(time.monotonic()),
            })
        print("#{:<11}| Me: ".format(self.channel_name), end="", flush=True)

        message_id = self.max_message_id
        self.max_message_id += 1
        return message_id

    def say_complete(self, sendable_text, *, channel_id, thread_id = None, timeout = 5):
        self.say(sendable_text, channel_id=channel_id, thread_id=thread_id)
        return self.messages[-1]["ts"]

    def react(self, channel_id, timestamp, emoticon):
        assert self.get_channel_name_by_id(channel_id) is not None, "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        assert isinstance(timestamp, str), "`timestamp` must be a string rather than \"{}\"".format(timestamp)
        assert isinstance(emoticon, str), "`emoticon` must be a string rather than \"{}\"".format(emoticon)

        target_message = next((m for m in self.messages if m["ts"] == timestamp), None)
        assert target_message is not None, "Invalid timestamp - can't find message with timestamp \"{}\"".format(timestamp)

        self.logger.info("adding reaction :{}: to message with timestamp {} in channel {}".format(emoticon, timestamp, self.get_channel_name_by_id(channel_id)))
        print("\r\033[K" + "#{:<11}| Botty reacted to \"{}\" with :{}:".format(self.get_channel_name_by_id(channel_id), target_message["text"], emoticon)) # clear the current line using Erase in Line ANSI escape code
        print("#{:<11}| Me: ".format(self.channel_name), end="", flush=True)

    def unreact(self, channel_id, timestamp, emoticon):
        assert self.get_channel_name_by_id(channel_id) is not None, "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        assert isinstance(timestamp, str), "`timestamp` must be a string rather than \"{}\"".format(sendable_text)
        assert isinstance(emoticon, str), "`emoticon` must be a string rather than \"{}\"".format(sendable_text)

        target_message = next((m for m in self.messages if m["ts"] == timestamp), None)
        assert target_message is not None, "Invalid timestamp - can't find message with timestamp \"{}\"".format(timestamp)

        self.logger.info("removing reaction :{}: to message with timestamp {} in channel {}".format(emoticon, timestamp, self.get_channel_name_by_id(channel_id)))
        print("\r\033[K" + "#{:<11}| Botty unreacted to \"{}\" with {}".format(self.get_channel_name_by_id(channel_id), target_message["text"], emoticon)) # clear the current line using Erase in Line ANSI escape code
        print("#{:<11}| Me: ".format(self.channel_name), end = "", flush=True)

    def get_channel_name_by_id(self, channel_id):
        assert isinstance(channel_id, str), "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        return channel_id[1:]

    def get_channel_id_by_name(self, channel_name):
        assert isinstance(channel_name, str), "`channel_name` must be a valid channel name rather than \"{}\"".format(channel_name)
        channel_name = channel_name.strip().lstrip("#")
        return "C{}".format(channel_name)

    def get_user_name_by_id(self, user_id):
        assert isinstance(user_id, str), "`user_id` must be a valid user ID rather than \"{}\"".format(user_id)
        return user_id[1:]

    def get_user_id_by_name(self, user_name):
        assert isinstance(user_name, str), "`user_name` must be a valid username rather than \"{}\"".format(user_name)
        user_name = user_name.strip().lstrip("@")
        return "U{}".format(user_name)

    def get_direct_message_channel_id_by_user_id(self, user_id):
        return "D{}".format(user_id)

    def get_user_info_by_id(self, user_id):
        assert isinstance(user_id, str), "`user_id` must be a valid user ID rather than \"{}\"".format(user_id)
        return {
            "color": "ff0000",
            "id": "UMe", "name": "Me",
            "deleted": False, "is_admin": False, "is_bot": False, "is_owner": False, "is_primary_owner": False, "is_restricted": False, "is_ultra_restricted": False,
            "profile": {"email": "me@example.com", "first_name": "Some", "last_name": "Body", "real_name": "Some Body"},
            "real_name": "Some Body",
            "tz": "Canada/Eastern", "tz_label": "Eastern Daylight Time", "tz_offset": -25200,
        }

    def get_user_is_bot(self, user_id):
        return False

    def administrator_console(self, namespace):
        raise NotImplementedError("The administrator console is not supported in the debug Slack bot.")

class IrlSlackBot(SlackBot):
    """
    Slack debug bot - when started, exposes a command line interface for testing and debugging your Slack bot.

    This class is designed to emulate the functionality of the `SlackBot` class as closely as possible. For method documentation, refer to the corresponding methods in the `SlackBot` class.
    """
    def __init__(self, token, logger=None):
        assert isinstance(token, str), "`token` must be a valid Slack API token"
        assert logger is None or not isinstance(logger, logging.Logger), "`logger` must be `None` or a logging function"

        if logger is None: self.logger = logging.getLogger(self.__class__.__name__)
        else: self.logger = logger

        self.messages = []

        self.max_message_id = 1
        self.channel_name = "general"
        self.bot_user_id = "botty"
        if os.path.exists("temp_music"):
            shutil.rmtree("temp_music")
        os.mkdir("temp_music")
        self.music_counter = 0

    def start_loop(self): self.start()

    def start(self):
        import threading, queue
        import readline # this makes arrow keys work for input()

        print("##########################################")
        print("#   Botty IRL Environment   #")
        print("##########################################")
        print()
        print("This is a local chat containing only you and Botty.")
        print()
        print("The following slash commands are available:")
        print()
        print("    /react -3 eggplant        | reacts to the third most recent text message with an eggplant")
        print("    /unreact 1 heart          | removes the heart reaction from the second earliest text message")
        print("    /reply -1 yeah definitely | replies to the most recent text message with \"yeah definitely\"")
        print("    /channel random           | moves you and Botty to the #random channel")
        print()

        user_input_queue = queue.Queue()
        def accept_input():
            while True:
                try:
                    text = input("\r\033[K" + "#{:<11}| Me: ".format(self.channel_name)) # clear the current line using Erase in Line ANSI escape code (this allows us to overwrite the existing prompt if present)
                except EOFError:
                    user_input_queue.put(None)
                    return

                user_input_queue.put(text)
                user_input_queue.join() # wait for the task to finish processing before allowing input again
        input_thread = threading.Thread(target=accept_input, daemon=True) # thread dies when main thread (the only non-daemon thread) exits
        input_thread.start()

        try:
            while True:
                self.on_step()
                while not user_input_queue.empty():
                    user_input = user_input_queue.get()
                    if user_input is None: raise KeyboardInterrupt # end of user input
                    self.handle_user_input(user_input)
                    user_input_queue.task_done()
                time.sleep(0.01)
        except KeyboardInterrupt: pass

    def handle_user_input(self, text):
        # handle normal message
        message = {
            "type": "message",
            "channel": "C" + self.channel_name,
            "user": "UMe",
            "text": self.text_to_sendable_text(text),
            "ts": str(time.monotonic()),
        }
        self.messages.append(message)
        self.on_message(message)

    def say(self, sendable_text, *, channel_id, thread_id = None):
        assert self.get_channel_name_by_id(channel_id) is not None, "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        assert isinstance(thread_id, str) or thread_id is None, "`thread_id` must be a valid Slack timestamp or None, rather than \"{}\"".format(thread_id)
        assert isinstance(sendable_text, str), "`sendable_text` must be a string rather than \"{}\"".format(sendable_text)

        if thread_id is not None: # message in a thread
            thread_first_message = next((m for m in self.messages if m["ts"] == thread_id), None)
            assert thread_first_message is not None, "Invalid thread ID - can't find message with timestamp \"{}\"".format(thread_id)

            self.logger.info("sending message to channel {} (in thread {}): {}".format(self.get_channel_name_by_id(channel_id), thread_id, sendable_text))
            print("\r\033[K" + "#{:<11}| Botty (in thread for \"{}\"): {}".format(self.get_channel_name_by_id(channel_id), thread_first_message["text"], sendable_text)) # clear the current line using Erase in Line ANSI escape code
            self.messages.append({
                "type": "message",
                "channel": "C" + self.channel_name,
                "user": "UBotty",
                "text": sendable_text,
                "ts": str(time.monotonic()),
                "thread_ts": thread_id,
            })
        else: # top-level message
            self.logger.info("sending message to channel {}: {}".format(self.get_channel_name_by_id(channel_id), sendable_text))
            print("\r\033[K" + "#{:<11}| Botty: {}".format(self.get_channel_name_by_id(channel_id), sendable_text)) # clear the current line using Erase in Line ANSI escape code
            self.messages.append({
                "type": "message",
                "channel": "C" + self.channel_name,
                "user": "UBotty",
                "text": sendable_text,
                "ts": str(time.monotonic()),
            })

        # Send over Bluetooth
        self.flail()

        #text to speech
        tts = gTTS(text=sendable_text, lang='en')
        self.music_counter += 1
        tts.save("temp_music\\temp" + str(self.music_counter) + ".mp3")
        mixer.init()
        mixer.music.load("temp_music\\temp" + str(self.music_counter) + ".mp3") # you may use .mp3 but support is limited
        mixer.music.play()

        print("#{:<11}| Me: ".format(self.channel_name), end="", flush=True)

        message_id = self.max_message_id
        self.max_message_id += 1
        return message_id

    def say_complete(self, sendable_text, *, channel_id, thread_id = None, timeout = 5):
        self.say(sendable_text, channel_id=channel_id, thread_id=thread_id)
        return self.messages[-1]["ts"]

    def get_channel_name_by_id(self, channel_id):
        assert isinstance(channel_id, str), "`channel_id` must be a valid channel ID rather than \"{}\"".format(channel_id)
        return channel_id[1:]

    def get_channel_id_by_name(self, channel_name):
        assert isinstance(channel_name, str), "`channel_name` must be a valid channel name rather than \"{}\"".format(channel_name)
        channel_name = channel_name.strip().lstrip("#")
        return "C{}".format(channel_name)

    def get_user_name_by_id(self, user_id):
        assert isinstance(user_id, str), "`user_id` must be a valid user ID rather than \"{}\"".format(user_id)
        return user_id[1:]

    def get_user_id_by_name(self, user_name):
        assert isinstance(user_name, str), "`user_name` must be a valid username rather than \"{}\"".format(user_name)
        user_name = user_name.strip().lstrip("@")
        return "U{}".format(user_name)

    def get_direct_message_channel_id_by_user_id(self, user_id):
        return "D{}".format(user_id)

    def get_user_info_by_id(self, user_id):
        assert isinstance(user_id, str), "`user_id` must be a valid user ID rather than \"{}\"".format(user_id)
        return {
            "color": "ff0000",
            "id": "UMe", "name": "Me",
            "deleted": False, "is_admin": False, "is_bot": False, "is_owner": False, "is_primary_owner": False, "is_restricted": False, "is_ultra_restricted": False,
            "profile": {"email": "me@example.com", "first_name": "Some", "last_name": "Body", "real_name": "Some Body"},
            "real_name": "Some Body",
            "tz": "Canada/Eastern", "tz_label": "Eastern Daylight Time", "tz_offset": -25200,
        }

    def get_user_is_bot(self, user_id):
        return False

    def administrator_console(self, namespace):
        raise NotImplementedError("The administrator console is not supported in the debug Slack bot.")
