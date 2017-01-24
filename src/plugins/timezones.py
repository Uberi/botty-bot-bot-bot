#!/usr/bin/env python3

import re
from datetime import datetime, date

import pytz

from .utilities import BasePlugin
from .utilities import clockify, untag_word

timezone_abbreviations = {
    "est":        pytz.timezone("Canada/Eastern"),
    "edt":        pytz.timezone("Canada/Eastern"),
    "atlantic":   pytz.timezone("Canada/Eastern"),
    "eastern":    pytz.timezone("Canada/Eastern"),
    "toronto":    pytz.timezone("Canada/Eastern"),
    "waterloo":   pytz.timezone("Canada/Eastern"),
    "ontario":    pytz.timezone("Canada/Eastern"),
    "ny":         pytz.timezone("US/Eastern"),
    "pst":        pytz.timezone("Canada/Pacific"),
    "vancouver":  pytz.timezone("Canada/Pacific"),
    "pacific":    pytz.timezone("US/Pacific-New"),
    "sf":         pytz.timezone("US/Pacific-New"),
    "la":         pytz.timezone("US/Pacific-New"),
    "california": pytz.timezone("US/Pacific-New"),
}

other_timezones = (
    ("toronto",   pytz.timezone("Canada/Eastern")),
    ("vancouver", pytz.timezone("Canada/Pacific")),
    ("utc",       pytz.utc),
)

class TimezonesPlugin(BasePlugin):
    """
    Timezone conversion plugin for Botty.

    Example invocations:

        #general    | Me: 4pm local
        #general    | Botty: *EASTERN DAYLIGHT TIME* (Μe's local time) :clock4: 16:00 :point_right: *TORONTO* :clock4: 16:00 - *VANCOUVER* :clock1: 13:00 - *UTC* :clock8: 20:00
        #general    | Me: 6:23pm pst
        #general    | Botty: *PST* :clock630: 18:23 :point_right: *TORONTO* :clock930: 21:23 - *VANCOUVER* :clock630: 18:23 - *UTC* :clock130: 1:23 (tomorrow)
        #general    | Me: 6:23 here
        #general    | Botty: *EASTERN DAYLIGHT TIME* (Μe's local time) :clock630: 6:23 :point_right: *TORONTO* :clock630: 6:23 - *VANCOUVER* :clock330: 3:23 - *UTC* :clock1030: 10:23
        #general    | Me: 8pm toronto
        #general    | Botty: *TORONTO* :clock8: 20:00 :point_right: *TORONTO* :clock8: 20:00 - *VANCOUVER* :clock5: 17:00 - *UTC* :clock12: 0:00 (tomorrow)
    """
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, m):
        if not m.is_user_text_message: return False
        match = re.search(r"\b(\d\d?)(?::(\d\d))?(?:\s*(am|pm))?\s+(\w+)", m.text, re.IGNORECASE)
        if not match: return False

        # get time of day
        if not match.group(2) and not match.group(3): return False # ignore plain numbers like "4 potato"
        hour = int(match.group(1))
        minute = 0 if match.group(2) is None else int(match.group(2))
        if not (0 <= hour <= 23) or not (0 <= minute <= 59): return False
        if match.group(3) is not None and match.group(3).lower() == "pm":
            if not (1 <= hour <= 12): return False
            hour = (hour % 12) + 12
        today = date.today()
        naive_timestamp = datetime(today.year, today.month, today.day, hour, minute)
        timezone_name = match.group(4)

        # get timezone and localized timestamp
        if timezone_name.lower() in timezone_abbreviations: # use the specified timezone
            timezone = timezone_abbreviations[timezone_name.lower()]
            timezone_is_from_user_info = False
        elif timezone_name.lower() in {"local", "here"}: # use the user's local timezone, specified in their profile
            user_info = self.get_user_info_by_id(m.user_id)
            try:
                timezone = pytz.timezone(user_info.get("tz"))
            except: # user does not have a valid timezone
                return False
            timezone_name = user_info.get("tz_label")
            timezone_is_from_user_info = True
        else:
            return False
        timestamp = timezone.localize(naive_timestamp)

        # perform timezone conversions
        timezone_conversions = []
        for other_timezone_name, other_timezone in other_timezones:
            converted_timestamp = timestamp.astimezone(other_timezone)
            if converted_timestamp.date() > timestamp.date():
                timezone_conversions.append("*{}* :{}: {}:{:>02} (tomorrow)".format(other_timezone_name.upper(), clockify(converted_timestamp), converted_timestamp.hour, converted_timestamp.minute))
            elif converted_timestamp.date() < timestamp.date():
                timezone_conversions.append("*{}* :{}: {}:{:>02} (yesterday)".format(other_timezone_name.upper(), clockify(converted_timestamp), converted_timestamp.hour, converted_timestamp.minute))
            else:
                timezone_conversions.append("*{}* :{}: {}:{:>02}".format(other_timezone_name.upper(), clockify(converted_timestamp), converted_timestamp.hour, converted_timestamp.minute))

        if timezone_is_from_user_info:
            selected_time = "(timezone from {}'s profile) *{}* :{}: {}:{:>02}".format(untag_word(self.get_user_name_by_id(m.user_id)), timezone_name.upper(), clockify(timestamp), timestamp.hour, timestamp.minute)
        else:
            selected_time = "*{}* :{}: {}:{:>02}".format(timezone_name.upper(), clockify(timestamp), timestamp.hour, timestamp.minute)

        self.respond_raw("{} :point_right: {}".format(selected_time, " - ".join(timezone_conversions)))
        return True
