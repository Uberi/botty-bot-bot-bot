#!/usr/bin/env python3

import re, json
from functools import lru_cache

import requests

from .utilities import BasePlugin

UW_API_KEY = "123afda14d0a233ecb585591a95e0339"
UW_API_BASE = "http://api.uwaterloo.ca/v2/"

@lru_cache(maxsize=128)
def uwapi(endpoint, params={}):
    params["key"] = UW_API_KEY
    r = requests.get(UW_API_BASE + endpoint + ".json", params=params)
    assert r.status_code == 200
    value = r.json()
    return value["data"]

class UWCoursesPlugin(BasePlugin):
    """
    UW course lookup plugin for Botty.

    Example invocations:

        #general    | Me: uw course cs341
        #general    | Botty: *CS 341* _(offered F, W, S)_: Algorithms (http://www.ucalendar.uwaterloo.ca/1516/COURSE/course-CS.html#CS341)
    """
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, message):
        text = self.get_message_text(message)
        if text is None: return False
        match = re.search(r"^\s*uw\s+courses?\s+([^,]+(?:,[^,]+)*)", text, re.IGNORECASE)
        if not match: return False
        query = match.group(1)

        # query for the course information
        result = []
        for course in query.split(","):
            match = re.search(r"([a-zA-Z]+)\s*(\w+)", course)
            if not match: continue
            subject, catalog = match.group(1), match.group(2)
            course_entry = uwapi("courses/{}/{}.json".format(subject, catalog))
            result.append("*{subject} {catalog}* (offered {offered}): {title} ({url})".format(
                subject=course_entry["subject"], catalog=course_entry["catalog_number"],
                title=course_entry["title"], url=course_entry["url"],
                offered=", ".join(course_entry["terms_offered"])
            ))

        if result: self.respond_raw("\n".join(result))

        return True
