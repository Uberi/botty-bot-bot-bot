#!/usr/bin/env python3

import re, json, time
from os import path
from datetime import datetime

import recurrent
import dateutil.rrule

from ..utilities import BasePlugin

SAVED_REMINDERS_FILE = path.join(path.dirname(path.realpath(__file__)), "saved_reminders.json")

class RemindersPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

        self.last_reminder_check_time = 0

        # load saved reminders
        try:
            with open(SAVED_REMINDERS_FILE, "r") as f:
                self.reminders = [
                    [
                        datetime.fromtimestamp(entry["next_occurrence"]),
                        entry["recurrence"],
                        entry["channel"],
                        entry["description"],
                    ]
                    for entry in json.load(f)
                ]
        except FileNotFoundError:
            self.reminders = []

    def on_step(self):
        # check reminders no more than once every 30 seconds
        current_time = time.time()
        if current_time - self.last_reminder_check_time < 30: return False
        self.last_reminder_check_time = current_time

        now = datetime.now()
        new_reminders = []
        reminders_updated = False
        for occurrence, recurrence, channel, description in self.reminders:
            if occurrence <= now: # reminder triggered, send notification
                reminders_updated = True
                if recurrence is not None: # recurring reminder, set up the next one
                    rrule = dateutil.rrule.rrulestr(recurrence)
                    next_occurrence = rrule.after(now) # get the next occurrence after the current one
                    if next_occurrence is not None:
                        new_reminders.append([next_occurrence, recurrence, channel, description])
                else:
                    next_occurrence = None
                self.remind(occurrence, next_occurrence, channel, description)
            else: # reminder has not triggered yet
                new_reminders.append([occurrence, recurrence, channel, description])
        if reminders_updated: self.save_reminders(new_reminders)
        self.reminders = new_reminders
        return True

    def on_message(self, message):
        text = self.get_text_message_body(message)
        if text is None: return False
        match = re.search(r"^\s*\bbotty[\s,\.]+remind\s+(\S+)\s+(.*?):\s+(.*)", text, re.IGNORECASE)
        if match:
            channel_name = match.group(1)
            occurrences = match.group(2).strip()
            description = match.group(3).strip()

            # ensure channel is valid
            if self.get_channel_id_by_name(channel_name) is None:
                self.respond("what kind of channel is \"{}\" anyway".format(channel_name))
                return True

            # parse event occurrences
            try:
                r = recurrent.RecurringEvent()
                rrule_or_datetime = r.parse(occurrences)
                if rrule_or_datetime is None: raise ValueError
            except: # unknown or invalid event occurrences format
                self.respond("what's \"{}\" supposed to mean".format(occurrences))
                return True

            if isinstance(rrule_or_datetime, datetime): # single occurrence reminder
                self.reminders.append([rrule_or_datetime, None, channel_name, description])
                self.respond("reminder for \"{}\" set at {}".format(description, rrule_or_datetime))
            else: # repeating reminder
                rrule = dateutil.rrule.rrulestr(rrule_or_datetime)
                next_occurrence = rrule.after(datetime.now())
                if next_occurrence is None:
                    self.respond("\"{}\" will never trigger, rrule is {}".format(occurrences, rrule_or_datetime))
                    return True
                self.reminders.append([next_occurrence, rrule_or_datetime, channel_name, description])
                self.respond("recurring reminder for \"{}\" set, next reminder is at {}".format(description, next_occurrence))
            self.save_reminders(self.reminders)
            return True

        match = re.search(r"^\s*\bbotty[\s,\.]+(?:unremind|stop\s+reminding\s+(?:us\s+)?about|stop\s+reminders?\s+for)\s+(.*)", text, re.IGNORECASE)
        if match:
            description = match.group(1).strip()
            new_reminders = [r for r in self.reminders if r[3] != description]
            if len(new_reminders) < len(self.reminders):
                self.respond("removed reminder for \"{}\"".format(description))
                self.save_reminders(new_reminders)
            else:
                self.respond("there was already no reminder for \"{}\"".format(description))
            self.reminders = new_reminders
            return True
        
        return False

    def remind(self, occurrence_time, next_occurrence, channel, description):
        if next_occurrence is None:
            self.say(self.get_channel_id_by_name(channel), "*REMINDER:* {}".format(description))
        else:
            self.say(self.get_channel_id_by_name(channel), "*REMINDER (NEXT REMINDER SET TO {}):* {}".format(next_occurrence, description))
    
    def save_reminders(self, reminders):
        self.logger.info("saving {} reminders...".format(len(self.reminders)))
        entries = [
            {
                "next_occurrence": time.mktime(reminder[0].timetuple()),
                "recurrence":      reminder[1],
                "channel":         reminder[2],
                "description":     reminder[3],
            }
            for reminder in reminders
        ]
        with open(SAVED_REMINDERS_FILE, "w") as f:
            json.dump(entries, f, sort_keys=True, indent=4, separators=(",", ": "))

if __name__ == "__main__":
    "botty remind #music every monday at 3pm: :fire: :fire: :fire: NEW NOON PACIFIC MIXTAPE IS OUT :fire: :fire: :fire:"