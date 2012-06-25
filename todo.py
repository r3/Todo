#!/usr/bin/env python
"""Trivial Todo

    https://github.com/r3/Todo


    Trivial Todo is a command line driven program used to track reminders. It
    is capable of handling due dates, catagories for your reminders, and more.
    Use `todo --help` for a complete list of options.
"""

import shelve
import datetime
import argparse

from itertools import chain
from contextlib import closing

STREAM = 'todo.shelve'


# Each added reminder is an instance of the following class
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


# Exceptions used when adding or removing reminders or parsing a date
class ReminderExistsException(Exception):
    pass


class ReminderDoesNotExistException(Exception):
    pass


class InvalidDateException(Exception):
    pass


# Implementation details
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


# Workhorse functions called by argument functions
def search_field(target, field):
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


def delete_reminder(reminder):
    """Removes a reminder if one exists"""
    if not reminder_exists(reminder):
        raise ReminderDoesNotExistException("The reminder that you're"
               " attempting to remove does not exist.")

    _remove_reminder(reminder)


def parse_date(date):
    """Parses date strings such as 'tomorrow' or '03/08' to valid datetime"""
    pass


# Argument functions called depending on subparser used
def add(args):
    """Called by the 'add' subparser"""
    reminder = Reminder(**args)
    add_reminder(reminder)


def remove(args):
    """Called by the 'remove' subparser"""
    pass


def search(args):
    """Called by the 'search' subparser"""
    pass


def show(args):
    """Called by the 'show' subparser"""
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=("Trivial todo keeps track"
        " of your reminders!"))
    subparsers = parser.add_subparsers(help="Commands for todo:")

    # Add reminders
    parser_add = subparsers.add_parser('add', help="Add reminders")
    parser_add.add_argument('content', help="Text for your reminder",
            required=True)
    parser_add.add_argument('--catagory', help="Catagory of your reminder")
    parser_add.add_argument('--due', help="Due date for your reminder",
            dest='date_due')
    parser_add.set_defaults(func=add)

    # Remove reminders
    parser_remove = subparsers.add_parser('remove', help="Remove reminders")
    parser_remove.add_argument('serial', help="Numer of reminder to remove",
            required=True)
    parser_remove.add_argument('--yes', action='store_const', const=True,
            help="Confirms the removal of reminder", dest='confirm',
            default=None)
    parser_remove.set_defaults(func=remove)

    # Search reminders
    parser_search = subparsers.add_parser('search', help="Search reminders")
    parser_search.add_argument('content', help="Find reminders by content")
    parser_search.add_argument('--due', help="Find reminders by due date")
    parser_search.set_defaults(func=search)

    # Show reminders
    parser_show = subparsers.add_parser('show', help="Show reminders")
    parser_show.add_argument('--number', help="Show a reminder by its number")
    parser_show.add_argument('--catagory', help="Show reminders in a catagory")
    parser_show.set_defaults(func=show)

    args = parser.parse_args()
