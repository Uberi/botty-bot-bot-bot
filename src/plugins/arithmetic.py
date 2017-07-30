#!/usr/bin/env python3

import re, random
import token
import multiprocessing

import sympy
from sympy.core import numbers
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, implicit_multiplication, implicit_application
from sympy.parsing.sympy_tokenize import TokenError
from sympy.physics import units

from .utilities import BasePlugin

ALLOWED_TOKENS = {
    token.ENDMARKER,  token.NAME,      token.NUMBER,     token.STRING,       token.LPAR,
    token.RPAR,       token.LSQB,      token.RSQB,       token.COMMA,        token.PLUS,
    token.MINUS,      token.STAR,      token.SLASH,      token.VBAR,         token.AMPER,
    token.LESS,       token.GREATER,   token.PERCENT,    token.LBRACE,       token.RBRACE,
    token.EQEQUAL,    token.NOTEQUAL,  token.LESSEQUAL,  token.GREATEREQUAL, token.TILDE,
    token.CIRCUMFLEX, token.LEFTSHIFT, token.RIGHTSHIFT, token.DOUBLESTAR,   token.DOUBLESLASH,
    token.AT,
}
ALLOWED_OPS = {"(", ")", "[", "]", ",", "+", "-", "*", "/", "|", "&", "<", ">", "%", "{", "}", "==", "!=", "<=", ">=", "~", "^", "<<", ">>", "**", "//", "@"}
ALLOWED_NAMESPACE = {
    name: getattr(sympy, name) for name in
    {"Abs", "E", "Eq", "Float", "I", "Integer", "Symbol", "acos", "acosh", "acot", "acoth", "acsc", "asec", "asech", "asin", "asinh", "atan", "atan2", "atanh", "ceiling", "comp", "compose", "conjugate", "cos", "cosh", "cot", "coth", "csc", "csch", "decompose", "deg", "degree", "denom", "diff", "div", "divisors", "exp", "expand", "factor", "factorial", "false", "floor", "gamma", "gcd", "im", "integrate", "invert", "is_decreasing", "is_increasing", "is_monotonic", "is_strictly_decreasing", "is_strictly_increasing", "isolate", "isprime", "latex", "lcm", "li", "limit", "limit_seq", "ln", "log", "nan", "nroots", "nsimplify", "nsolve", "numer", "oo", "pi", "primefactors", "prod", "product", "quo", "rad", "re", "real_roots", "refine", "refine_root", "rem", "roots", "satisfiable", "sec", "sech", "sign", "simplify", "sin", "sinc", "sinh", "solve", "sqrt", "subsets", "summation", "tan", "tanh", "to_cnf", "to_dnf", "to_nnf", "true"}
}
ALLOWED_NAMESPACE.update({
    name: getattr(units, name) for name in dir(units)
    if type(getattr(units, name)) in [units.dimensions.Dimension, units.prefixes.Prefix, units.quantities.Quantity]
})

def whitelist_tokens(tokens, local_dict, global_dict):
    for token_type, token_value in tokens:
        if token_type in ALLOWED_TOKENS:
            continue
        if token_type == token.OP and token_value in ALLOWED_OPS:
            continue
        raise TokenError("forbidden token {}".format(token_type))
    return tokens

def evaluate_with_time_limit(text, time_limit=1):
    def evaluate(queue, text):
        subs = {
            sympy.Symbol(k): v for k, v in units.__dict__.items()
            if (isinstance(v, sympy.Expr) and v.has(units.Unit)) or isinstance(v, sympy.Integer)
        }
        try:
            transformations = (whitelist_tokens,) + standard_transformations + (implicit_multiplication, implicit_application)
            expression = parse_expr(text, local_dict=ALLOWED_NAMESPACE, global_dict={}, transformations=transformations)
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
    """
    Symbolic mathematics plugin for Botty.

    This uses Sympy for computation and implements evaluation timeouts by spawning a child process and killing it if it takes too much time.

    Example invocations:

        #general    | Me: ca sqrt(20)
        #general    | Botty: sqrt(20) :point_right: 2*sqrt(5) :point_right: 4.4721359549995793928183473374625524708812367192230514485417944908210418512756098
        #general    | Me: calculate integrate(1/x, x)
        #general    | Botty: integrate(1/x, x) :point_right: log(x)
        #general    | Me: calculate 1kg meter/second**2 + 2 newtons
        #general    | Botty: 1kg meter/second**2 + 2 newtons :point_right: 3*kg*m/s**2
        #general    | Me: eval solve(Eq(x**2, 6), x)
        #general    | Botty: solve(Eq(x**2, 6), x) :point_right: [-sqrt(6), sqrt(6)]
    """
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, m):
        if not m.is_user_text_message: return False
        match = re.search(r"^\s*\b(?:ca(?:lc(?:ulate)?)?|eval(?:uate)?)\s+(.+)", m.text, re.IGNORECASE)
        if not match: return False
        query = self.sendable_text_to_text(match.group(1)) # get query as plain text in order to make things like < and > work (these are usually escaped)

        expression = evaluate_with_time_limit(query)
        if isinstance(expression, Exception): # evaluation resulted in error
            message = random.choice(["s a d e x p r e s s i o n s", "wat", "results hazy, try again later", "cloudy with a chance of thunderstorms", "oh yeah, I learned all about that in my sociology class", "eh too lazy, get someone else to do it", "would you prefer the truth or a lie?", "nice try", "you call that an expression?"])
            self.respond_raw("{} ({})".format(message, expression), as_thread=True)
        elif expression is None: # evaluation timed out
            self.respond_raw("tl;dr", as_thread=True)
        else: # evaluation completed successfully
            if hasattr(expression, "evalf") and not isinstance(expression, numbers.Integer) and not isinstance(expression, numbers.Float):
                value = expression.evalf(80)
                if value == sympy.zoo: formatted_value = "(complex infinity)"
                elif value == sympy.oo: formatted_value = "\u221e"
                else: formatted_value = str(value)
                if str(value) == str(expression) or str(query) == str(expression): self.respond_raw("{} :point_right: {}".format(query, formatted_value))
                else: self.respond_raw("{} :point_right: {} :point_right: {}".format(query, expression, formatted_value))
            else:
                self.respond_raw("{} :point_right: {}".format(query, expression))
        return True

if __name__ == "__main__":
    print(evaluate_with_time_limit("integrate(1/x, x)"))
    print(evaluate_with_time_limit("1+/a"))
    print(evaluate_with_time_limit("1kg meter/second**2 + 2 newtons"))
