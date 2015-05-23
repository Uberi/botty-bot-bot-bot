import re

import wikipedia

def send(client, channel_id, text): client.rtm_send_message(channel_id, text)

def process_chat_message(client, user, channel_id, text, timestamp):
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
    result = re.search(r"\b(?:who\s+is|who's)\s+([^,]+|\"[^\"]+\")", text, re.IGNORECASE)
    if result:
        pass

# evaluate arithmetic expressions safely
import ast
import operator as op
operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul, ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor, ast.USub: op.neg}
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
