#!/usr/bin/env python3

import re, json, sys, random
from datetime import datetime

import wikipedia

from markov import Markov

MESSAGE_DATA_FILE = "normalized_data.json"

def main():
    global markov

    # train a Markov model on the given chat data
    log("[INFO] LOADING CONVERSATION DATA...")
    data = json.load(open(MESSAGE_DATA_FILE, "r"))
    log("[INFO] TRAINING MARKOV MODEL...")
    markov = Markov(2) # Markov model with 2 word look-behind
    for message in Markov.tokenize_words(m[2] for m in data):
        markov.train(message)
    log("[INFO] MARKOV MODEL TRAINING COMPLETE")

def generate_sentence_starting_with(markov, first_part = ""):
    first_part = first_part.strip()
    words = next(Markov.tokenize_words([first_part])) if first_part != "" else []
    return Markov.format_words(words + markov.speak(words))

def process_text_message(client, user_id, channel_id, text, timestamp):
    global markov

    result = re.search(r"\bbotty[\s,\.]*(.*)", text, re.IGNORECASE)
    if result:
        query = result.group(1)
        try: send(client, channel_id, generate_sentence_starting_with(markov, query))
        except: send(client, channel_id, generate_sentence_starting_with(markov))
        return
    if random.random() < 0.01: # random chance of responding
        try: send(client, channel_id, generate_sentence_starting_with(markov, text))
        except: pass
        return

    result = re.search(r"\b(?:what\s+(?:is|are)|what's|wtf\s+(?:is|are))\s+([^,\?]+|\"[^\"]+\")", text, re.IGNORECASE)
    if result:
        query = result.group(1)
        
        # try to parse it as a math expression
        try:
            send(client, channel_id, "{} is {}".format(query, eval_expr(query)))
            return
        except: pass
        
        # try to search for it on wikipedia
        try: send(client, channel_id, "wikipedia says {} is \"{}\"".format(query, wikipedia.summary(query, sentences=2)))
        except wikipedia.exceptions.DisambiguationError as e: send(client, channel_id, "could be one of the following: " + "; ".join(e.args[1]))
        except: send(client, channel_id, "dunno")
        
        return
    result = re.search(r"\b(?:who\s+is|who's|who're)\s+([^,]+|\"[^\"]+\")", text, re.IGNORECASE)
    if result:
        send(client, channel_id, "who are you")
        return

# evaluate arithmetic expressions safely
import ast
import operator as op
operators = {
    ast.Add: op.add, ast.BitAnd: op.and_, ast.BitOr: op.or_, ast.BitXor: op.xor,
    ast.Div: op.truediv, ast.Eq: op.eq, ast.FloorDiv: op.floordiv, ast.Gt: op.gt,
    ast.GtE: op.ge, ast.Invert: op.inv, ast.LShift: op.lshift, ast.Lt: op.lt,
    ast.LtE: op.le, ast.Mod: op.mod, ast.Mult: op.mul, ast.Not: op.not_,
    ast.Pow: op.pow, ast.RShift: op.rshift, ast.Sub: op.sub, ast.USub: op.neg,
}
def eval_expr(value): return eval_tree(ast.parse(value, mode="eval").body)
def eval_tree(node):
    if isinstance(node, ast.Num): result = node.n
    elif isinstance(node, ast.UnaryOp): result = operators[type(node.op)](eval_tree(node.operand))
    elif isinstance(node, ast.BinOp):
        right = eval_tree(node.right)
        if type(node.op) == ast.Pow: assert right <= 1000
        result = operators[type(node.op)](eval_tree(node.left), right)
    else: raise TypeError(node)
    assert abs(result) <= 1e50
    return result

# Slack utilities
def send(client, channel_id, text): client.rtm_send_message(channel_id, text)
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

def log(value):
    print(datetime.now(), value, file=sys.stderr)
    sys.stderr.flush() # this is needed if redirecting to files

main()