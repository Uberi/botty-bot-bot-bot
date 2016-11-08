#!/usr/bin/env python3

import re, random
from ..utilities import BasePlugin

def weighted_choose(items):
    assert len(items), "`items` must be a non-empty collection"
    target = random.random() * sum(weight for item, weight in items)
    current = 0
    for item, weight in items:
        current += weight
        if current > target: return item
    return items[-1][0] # item weights didn't add up perfectly to 1, just return the last item

class SnekPlugin(BasePlugin):
    """
    Random snake emoji plugin for Botty.

    To set this up properly, add each image in `src/plugins/snek/emoji/*.png` to Slack as custom emoji. For example, `src/plugins/snek/emoji/snake_head.png` should be registered to the `:snake_head:` emoji, `src/plugins/snek/emoji/snake_tail4.png` with `:snake_tail4:`, and so on.

    The snake emoji in `src/plugins/snek/emoji/*.png` are hand painted with GIMP, as 16 by 16 transparent PNGs.

    Example invocations:

        #general    | Me: snek
        #general    | Botty: :snake_tail4::snake_body9::snake_body0::snake_body0::snake_body3::snake_body4::snake_body2::snake_body3::snake_body7::snake_body0::snake_body0::snake_body0::snake_body1::snake_body0::snake_body6::snake_body0::snake_head:
        #general    | Me: snaaaaake
        #general    | Botty: :snake_tail2::snake_body1::snake_body3::snake_body2::snake_body3::snake_body2::snake_body6::snake_body5::snake_head:
        #general    | Me: snakes???
        #general    | Botty: :snake_tail1::snake_body1::snake_body2::snake_body4::snake_body0::snake_body7::snake_body7::snake_body0::snake_body4::snake_body0::snake_body0::snake_body2::snake_body3::snake_body2::snake_body5::snake_head:
    """
    def __init__(self, bot):
        super().__init__(bot)
        self.snake_head = [
            ("snake_head", 1),
        ]
        self.snake_body = [
            ("snake_body0", 30),
            ("snake_body1", 20),
            ("snake_body2", 20),
            ("snake_body3", 20),
            ("snake_body4", 4),
            ("snake_body5", 4),
            ("snake_body6", 2),
            ("snake_body7", 2),
            ("snake_body8", 2),
            ("snake_body9", 2),
        ]
        self.snake_tail = [
            ("snake_tail0", 30),
            ("snake_tail1", 15),
            ("snake_tail2", 10),
            ("snake_tail3", 8),
            ("snake_tail4", 8),
        ]
        self.sample_length_distribution = lambda: random.randint(0, 25)

    def on_message(self, message):
        text = self.get_message_text(message)
        if text is None: return False
        match = re.search(r"\bs+n+[aeiou]+k+e*s*\b", text, re.IGNORECASE)
        if not match: return False

        snake_length = self.sample_length_distribution()
        snake_sequence = [weighted_choose(self.snake_tail)] + [weighted_choose(self.snake_body) for _ in range(snake_length)] + [weighted_choose(self.snake_head)]
        snake_message = "".join(":{}:".format(entry) for entry in snake_sequence)

        self.respond_raw(snake_message)
        return True
