#!/usr/bin/env python3

import re, json
from os import path
from datetime import datetime
from functools import lru_cache

import httplib2
import oauth2client
import apiclient
import dateutil.parser
from dateutil.tz import tzlocal
import requests

from ..utilities import BasePlugin

CALENDAR_ID = "uc21b9q2nr2ggquc3c6ahdgeo4@group.calendar.google.com" # calendar ID for W A T E R L O O B O Y S
SAVED_OAUTH_CREDENTIALS_FILE = path.join(path.dirname(path.realpath(__file__)), "oauth_credentials.json") # OAuth credentials, created by `src/plugins/events/get_oauth_credentials.py`

class EventsPlugin(BasePlugin):
    """
    Event calendar listing plugin for Botty.

    Example invocations:

        #general    | Me: sup botty
        #general    | Botty: UPCOMING EVENTS:
        • *Tech Talk: Defrobnicating The Gluon Manifold At Scale* from 16:00 to 16:30 on 2015-10-25 (Sunday) (http://tinyurl.com/usnrisy)
        • *Info Session: Oxygen - The New Killer App?* from 22:00 to 23:30 on 2015-10-26 (Monday) (http://tinyurl.com/xmentkx)
        • *Bloodmoon: The Bloodmoon Rises* from 17:30 2015-10-27 (Tuesday) to 02:30 2015-10-28 (Wednesday) (http://tinyurl.com/gydyusw)
        • *Wednesday Evening Grassroots Blues* from 19:00 to 23:00 on 2015-10-28 (Wednesday) (http://tinyurl.com/trcbvfa)
        • *Movie Night: Gun Woman Reloaded* from 19:00 2015-10-28 (Wednesday) to 00:30 2015-10-29 (Thursday) (http://tinyurl.com/sdfklea)
    """
    def __init__(self, bot):
        super().__init__(bot)

    @lru_cache() # cache recently used results to speed up repeated calls with the same parameters
    def shorten_url(self, url):
        request = requests.get("http://tinyurl.com/api-create.php", params={"url": url})
        request.raise_for_status()
        return request.text

    def on_message(self, message):
        text = self.get_message_text(message)
        if text is None: return False
        match = re.search(r"\b(?:sup\s+botty|wassup\s+botty|wh?at'?s\s+up\s+botty|botty\s+wassup|botty\s+what's\s+up|what\s+are\s+the\s+haps)\b", text, re.IGNORECASE)
        if not match: return False

        # obtain Google Calendar service
        store = oauth2client.file.Storage(SAVED_OAUTH_CREDENTIALS_FILE)
        credentials = store.get()
        assert credentials and not credentials.invalid, "No valid Google Calendar OAuth credentials available - run `python3 get_oauth_credentials.py` to create OAuth credentials."
        authorized_http = credentials.authorize(httplib2.Http())
        calendar_service = apiclient.discovery.build("calendar", "v3", http=authorized_http)

        start_timestamp = datetime.utcnow().isoformat() + "Z" # reference date for events - all events ending before this are excluded from the results
        eventsResult = calendar_service.events().list(
            calendarId = CALENDAR_ID,
            timeMin = start_timestamp,
            maxResults = 5,
            singleEvents = True,
            orderBy = "startTime"
        ).execute()
        events = eventsResult.get("items", [])

        now = datetime.now()
        result = []
        for event in events:
            if "dateTime" in event["start"]:
                start = dateutil.parser.parse(event["start"]["dateTime"]).astimezone(tzlocal()).replace(tzinfo=None) # start time in local time
            else:
                start = dateutil.parser.parse(event["start"]["date"])
            if "dateTime" in event["end"]:
                end = dateutil.parser.parse(event["end"]["dateTime"]).astimezone(tzlocal()).replace(tzinfo=None) # end time in local time
            else:
                end = dateutil.parser.parse(event["end"]["date"])
            summary = self.text_to_sendable_text(event["summary"])
            url = self.shorten_url(event["htmlLink"])
            if start.date() == end.date():
                result.append("\u2022 {}*{}* from {} to {} on {} ({})".format("[HAPPENING NOW] " if start <= now < end else "", summary, start.strftime("%H:%M"), end.strftime("%H:%M"), start.strftime("%Y-%m-%d (%A)"), url))
            else:
                result.append("\u2022 {}*{}* from {} to {} ({})".format("[HAPPENING NOW] " if start <= now < end else "", summary, start.strftime("%H:%M %Y-%m-%d (%A)"), end.strftime("%H:%M %Y-%m-%d (%A)"), url))
        self.respond("UPCOMING EVENTS:\n{}".format("\n".join(result)))

        return True
