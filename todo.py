import shelve
import datetime

from itertools import chain
from contextlib import closing

STREAM = 'todo.shelve'


class Reminder():
    """A reminder unit with a date, optional due date, catagory, and content"""
    def __init__(self, content=None, catagory=None, date_due=None, date=None):
        self.serial = Reminder.next_serial()
        self.date = date if date else datetime.datetime.now()
        self.content = content
        self.catagory = catagory if catagory else 'general'
        self.date_due = date_due

    def __eq__(self, other):
        """Attempts an equivalency match between two Reminders
           If a compared field in either Reminder is None, that field
           is ignored. The date the reminders were added is ignored.
        """
        for attrib in ('content', 'catagory', 'date_due'):
            self_attr = getattr(self, attrib)
            other_attr = getattr(other, attrib)

            if self_attr is None or other_attr is None:
                continue
            elif self_attr != other_attr:
                return False

        return True

    def __str__(self):
        return "{catagory}: {date} - {content} (Due: {date_due})".format(
                **self.__dict__)

    @staticmethod
    def next_serial():
        with _load_reminders() as reminders:
            serial = reminders.get('serial', 0)
            serial += 1
            reminders['serial'] = serial

        return serial


class ReminderExistsException(Exception):
    pass


class ReminderDoesNotExist(Exception):
    pass


def _load_reminders(stream=None):
    """Shortcut for loading the shelve with a context manager"""
    # Necessary to reload stream for testing purposes
    if stream is None:
        stream = STREAM
    return closing(shelve.open(stream))


def _iter_reminders():
    """Privides an iterator for all of the reminders"""
    with _load_reminders() as reminders:
        catagories = (reminders[x] for x in reminders.keys() if x != 'serial')
        for reminder in chain(*catagories):
            yield reminder


def _append_reminder(reminder):
    """Necessary to prevent writeback being required on the shelve"""
    with _load_reminders() as reminders:
        temp = reminders.get(reminder.catagory, [])
        temp.append(reminder)
        reminders[reminder.catagory] = temp


def _remove_reminder(reminder):
    """Necessary to prevent writeback being required on the shelve"""
    with _load_reminders() as reminders:
        temp = reminders.get(reminder.catagory, [])
        temp.remove(reminder)
        if not temp:
            del reminders[reminder.catagory]
        else:
            reminders[reminder.catagory] = temp


def search(target, field):
    """Returns all matching reminders based on a given field and target data
       Returns a list of matches
    """
    matches = []

    for reminder in _iter_reminders():
        if target == getattr(reminder, field):
            matches.append(reminder)

    return matches


def search_in_content(content):
    """Searches for reminders by partial content
       Returns a list of all matches
    """
    matches = []

    for reminder in _iter_reminders():
        if content in reminder.content:
            matches.append(reminder)

    return matches


def reminder_exists(reminder):
    """Check to determine of a reminder exists, returning a bool"""
    for item in _iter_reminders():
        if item == reminder:
            return True

    return False


def add_reminder(reminder):
    """Adds a reminder to the database unless it already exists"""
    if reminder_exists(reminder):
        raise ReminderExistsException("Reminder already exists")

    _append_reminder(reminder)
