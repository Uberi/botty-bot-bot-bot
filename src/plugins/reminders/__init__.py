#!/usr/bin/env python3

import re, json, time
from os import path
from datetime import datetime

import recurrent
import dateutil.rrule

from ..utilities import BasePlugin

SAVED_REMINDERS_FILE = path.join(path.dirname(path.realpath(__file__)), "saved_reminders.json")

class RemindersPlugin(BasePlugin):
    """
    Natural language reminders plugin for Botty.

    Supports one-time and recurring reminders. Reminders are persisted to `saved_reminders.json`.

    Any reminders that occur more often than once every 10 seconds will only occur at most once every 10 seconds.

    Example invocations:

        #general    | Me: botty remind me in 10 seconds: pineapple
        #general    | Botty: Me's reminder for "pineapple" set at 2015-09-01 22:13:58
        (10-20 seconds later)
        DM with Me  | Botty: *REMINDER:* pineapple
        #general    | Me: botty remind #random every 5 seconds: green
        (5-10 seconds later)
        #random     | Botty: *REMINDER:* green
        (10 seconds later)
        #random     | Botty: *REMINDER:* green
        (10 seconds later)
        #random     | Botty: *REMINDER:* green
        (...)
        
    """
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
        # check reminders no more than once every 10 seconds
        current_time = time.time()
        if current_time - self.last_reminder_check_time < 10: return False
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
        text, channel, user = self.get_message_text(message), self.get_message_channel(message), self.get_message_sender(message)
        if text is None or channel is None or user is None: return False
        user_name = self.get_user_name_by_id(user)

        # reminder setting command
        match = re.search(r"^\s*\bbotty[\s,\.]+remind\s+(\S+)\s+(.*?):\s+(.*)", text, re.IGNORECASE)
        if match:
            target_name = match.group(1).strip()
            occurrences = match.group(2).strip()
            description = match.group(3).strip()

            # validate channel ID
            if target_name == "me": target_name = self.get_user_name_by_id(user)
            if target_name == "us": target_name = self.get_channel_name_by_id(channel)
            target = self.get_channel_id_by_name(target_name)
            if target is None: # not a channel/private group/direct message
                target_user = self.get_user_id_by_name(target_name)
                if target_user is None: # not a user
                    self.respond("what kind of channel or user is \"{}\" anyway".format(target_name))
                    return True
                direct_message_channel = self.get_direct_message_channel_id_by_user_id(target_user)
                if direct_message_channel is None:
                    self.respond("there's no direct messaging with \"{}\"".format(target_name))
                    return True
                target = direct_message_channel

            # parse event occurrences
            try:
                r = recurrent.RecurringEvent()
                rrule_or_datetime = r.parse(occurrences)
                if rrule_or_datetime is None: raise ValueError
            except: # unknown or invalid event occurrences format
                self.respond("what's \"{}\" supposed to mean".format(occurrences))
                return True

            if isinstance(rrule_or_datetime, datetime): # single occurrence reminder
                self.reminders.append([rrule_or_datetime, None, target, description])
                self.say(target, "{}'s reminder for \"{}\" set at {}".format(user_name, description, self.text_to_sendable_text(str(rrule_or_datetime))))
            else: # repeating reminder
                rrule = dateutil.rrule.rrulestr(rrule_or_datetime)
                next_occurrence = rrule.after(datetime.now())
                if next_occurrence is None:
                    self.respond("\"{}\" will never trigger, rrule is {}".format(occurrences, self.text_to_sendable_text(rrule_or_datetime)))
                    return True
                self.reminders.append([next_occurrence, rrule_or_datetime, target, description])
                self.say(target, "{}'s recurring reminder for \"{}\" set, next reminder is at {}".format(user_name, description, self.text_to_sendable_text(str(next_occurrence))))
            self.save_reminders(self.reminders)
            return True

        # reminder unsetting command
        match = re.search(r"^\s*\bbotty[\s,\.]+(?:unremind|stop\s+reminding\s+(?:(?:us|me|them)\s+)?about|stop\s+reminders?\s+for)\s+(.*)", text, re.IGNORECASE)
        if match:
            description = match.group(1).strip()
            new_reminders = [r for r in self.reminders if r[3] != description]
            if len(new_reminders) < len(self.reminders):
                self.respond("removed reminder for \"{}\"".format(description))
                self.save_reminders(new_reminders)
            else:
                self.respond("there were already no reminders for \"{}\"".format(description))
            self.reminders = new_reminders
            return True

        return False

    def remind(self, occurrence_time, next_occurrence, channel, description):
        if self.get_channel_name_by_id(channel) is None: return # target no longer exists, it was probably removed
        if next_occurrence is None:
            self.say(channel, "*REMINDER:* {}".format(description))
        else:
            self.say(channel, "*REMINDER (NEXT REMINDER SET TO {}):* {}".format(self.text_to_sendable_text(str(next_occurrence)), description))
    
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
