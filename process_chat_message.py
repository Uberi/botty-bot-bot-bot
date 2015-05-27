import re, json, sys
from datetime import datetime

from markov import Markov

import wikipedia

def log(value):
    print(datetime.now(), value, file=sys.stderr)
    sys.stderr.flush() # this is needed if redirecting to files

# train a Markov model on the given chat data
log("[INFO] LOADING CONVERSATION DATA...")
try: data = json.load(open("normalized_data.json", "r"))
except: data = []
log("[INFO] TRAINING MARKOV MODEL...")
markov = Markov(2) # Markov model with 2 word look-behind
for message in Markov.tokenize_words(m[2] for m in data):
    markov.train(message)
log("[INFO] MARKOV MODEL TRAINING COMPLETE")

def generate_sentence_starting_with(first_part = ""):
    first_part = first_part.strip()
    words = next(Markov.tokenize_words([first_part])) if first_part != "" else []
    return Markov.format_words(words + markov.speak(words))

def send(client, channel_id, text): client.rtm_send_message(channel_id, text)

def process_chat_message(client, user, channel_id, text, timestamp):
    result = re.match(r"\s*botty[\s,\.]+(.*)", text, re.IGNORECASE)
    if result:
        query = result.group(1)
        try: send(client, channel_id, generate_sentence_starting_with(query))
        except: pass

    result = re.search(r"\b(?:what\s+(?:is|are)|what's|wtf\s+(?:is|are))\s+([^,]+|\"[^\"]+\")", text, re.IGNORECASE)
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
    ast.Add: op.add,
    ast.BitAnd: op.and_,
    ast.BitOr: op.or_,
    ast.BitXor: op.xor,
    ast.Div: op.truediv,
    ast.Eq: op.eq,
    ast.FloorDiv: op.floordiv,
    ast.Gt: op.gt,
    ast.GtE: op.ge,
    ast.Invert: op.inv,
    ast.LShift: op.lshift,
    ast.Lt: op.lt,
    ast.LtE: op.le,
    ast.Mod: op.mod,
    ast.Mult: op.mul,
    ast.Not: op.not_,
    ast.Pow: op.pow,
    ast.RShift: op.rshift,
    ast.Sub: op.sub,
    ast.USub: op.neg,
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
