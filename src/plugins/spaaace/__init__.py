#!/usr/bin/env python3

import re, os, random, io, json

from PIL import Image, ImageFont, ImageDraw, ImageFilter
from imgurpython import ImgurClient
from imgurpython.helpers.error import ImgurClientError

from ..utilities import BasePlugin

IMAGE_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), "backgrounds")
FONT_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "typewriter.ttf")
GENERATED_IMAGE_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "generated_image.jpg")
IMGUR_CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "imgur_credentials.json")

class SpaaacePlugin(BasePlugin):
    """
    Post images of a given quote set dramatically over a background.

    Example Invocations:

        #general    | Me: don't quote me on this, but botty's really got some cool features
        #general    | Botty: http://i.imgur.com/29eKFrz.jpg
    """
    def __init__(self, bot):
        super().__init__(bot)
        with open(IMGUR_CREDENTIALS_FILE, "r") as f:
            credentials = json.load(f)
            try:
                self.imgur_client = ImgurClient(credentials["client_id"], credentials["client_secret"])
            except ImgurClientError as e:
                self.logger.warning("Imgur client creation failed with `{}`, try checking the values in `{}`".format(e, IMGUR_CREDENTIALS_FILE))
                self.imgur_client = e

    def on_message(self, m):
        if not m.is_user_text_message: return False
        match = re.search(r"\bquote\s+me(?:\s+on\s+this)?\s*?,?\s+(?:but\s+)?(.+)", self.sendable_text_to_text(m.text), re.IGNORECASE)
        if not match: return False
        query = match.group(1)
        user_name = self.get_user_name_by_id(m.user_id)

        # fail gracefully if user has not configured this plugin yet
        if isinstance(self.imgur_client, ImgurClientError):
            self.respond_raw("oops, I don't have valid Imgur API credentials (`{}`) :( try checking the values in `{}`".format(self.imgur_client, IMGUR_CREDENTIALS_FILE))

        # generate segments of text
        segments = []
        for segment in query.split():
            if random.randint(0, 3) > 0 or not segments:
                segments.append(segment)
            else:
                segments[-1] += " " + segment
        segments.append("- " + user_name)

        # set up image for drawing
        image_file = os.path.join(IMAGE_FOLDER, random.choice(os.listdir(IMAGE_FOLDER)))
        background = Image.open(image_file).resize((1920, 1080), Image.BICUBIC)
        overlay = Image.new("RGBA", background.size, (0, 0, 0, 0))
        font = ImageFont.truetype(FONT_FILE, 48)
        overlay_draw = ImageDraw.Draw(overlay)

        # draw quote on the background
        padding = 20
        x, y = random.randint(20, 400), random.randint(200, 300)
        offset_x = x
        for segment in segments:
            w, h = overlay_draw.textsize(segment, font=font)
            w += padding * 2; h += padding * 2
            if offset_x + w > 1600 or segment.startswith("-"):
                x += random.randint(20, 200)
                offset_x = x
                y += 150
            offset_y = y + random.randint(-30, 30)
            overlay_draw.rectangle([(offset_x, offset_y), (offset_x + w, offset_y + h)], fill=(250, 240, 230))
            overlay_draw.text((offset_x + padding, offset_y + padding), segment, fill=(0, 0, 0), font=font)
            offset_x += w + random.randint(5, 40)
            overlay_draw = ImageDraw.Draw(overlay)
        overlay = overlay.filter(ImageFilter.GaussianBlur(radius=2))
        overlay = overlay.rotate(random.randint(-10, 10), resample=Image.BICUBIC)
        background.paste(overlay, mask=overlay)
        background.save(GENERATED_IMAGE_FILE, "JPEG")
        
        # upload image to imgur and post it in the channel
        result = self.imgur_client.upload_from_path(GENERATED_IMAGE_FILE, anon=True)
        self.respond_raw(result["link"])
        return True
