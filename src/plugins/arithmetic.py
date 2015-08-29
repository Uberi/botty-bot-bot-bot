#!/usr/bin/env python3

import re
import multiprocessing

import sympy
from sympy.parsing.sympy_parser import parse_expr
from sympy.core import numbers

from .utilities import BasePlugin

def evaluate_with_time_limit(text, time_limit=1):
    def evaluate(queue, text):
        try:
            expression = parse_expr(text)
            simplified_expression = sympy.simplify(expression)
            queue.put(simplified_expression)
        except Exception as e:
            queue.put(e)

    # run the evaluator in a separate process in order to enforce time limits
    queue = multiprocessing.SimpleQueue()
    process = multiprocessing.Process(target=evaluate, args=(queue, text))
    process.start()
    process.join(time_limit)
    if process.is_alive() or queue.empty():
        process.terminate()
        return None
    return queue.get()

class ArithmeticPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        match = re.search(r"^\s*\b(?:ca(?:lc(?:ulate)?)?|eval(?:uate)?)\s+(.+)", text, re.IGNORECASE)
        if not match: return False
        query = match.group(1)

        expression = evaluate_with_time_limit(query)
        if isinstance(expression, Exception): # evaluation resulted in error
            self.respond("bad expression, {}".format(expression))
        elif expression is None: # evaluation timed out
            self.respond("tl;dr")
        else: # evaluation completed successfully
            if hasattr(expression, "evalf") and not isinstance(expression, numbers.Integer) and not isinstance(expression, numbers.Float):
                self.respond("{} -> {} ({})".format(query, expression, expression.evalf(80)))
            else:
                self.respond("{} -> {}".format(query, expression))
        return True

if __name__ == "__main__":
    print(evaluate_with_time_limit("integrate(1/x, x)"))
    print(evaluate_with_time_limit("expand((x + 1)**4)"))
    print(evaluate_with_time_limit("1+/a"))
