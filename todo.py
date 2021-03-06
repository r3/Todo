#!/usr/bin/env python
"""Trivial Todo

    https://github.com/r3/Todo

    Author: Ryan Roler (ryan.roler@gmail.com)
    Requires: Python 2 or 3

    Trivial Todo is a command line driven program used to track reminders. It
    is capable of handling due dates, categories for your reminders, and more.
    Use `todo --help` for a complete list of options.

    A note on compatibility between 2 and 3: databases created in Python 3 are
    not backwards compatible as Python 3's pickle uses another protocol. Pick
    a version and stick with it, or create a new database.
"""

import sys
import shelve
import datetime
import argparse
import subprocess
import tempfile
import os

from itertools import chain
from contextlib import closing

HOME = os.path.join(os.getenv('HOME'), '.todo')
DB_NAME = 'database.shelve'
DB_LOCATION = os.path.join(HOME, DB_NAME)


# Each added reminder is an instance of the following class
class Reminder():
    """A reminder unit with a date, optional due date, category, and content"""
    def __init__(self, content=None, category=None, date_due=None, date=None):
        self.serial = Reminder.next_serial()
        self.date = date if date else datetime.date.today()
        self.content = content
        self.category = category if category else 'general'
        self.date_due = date_due

    def __eq__(self, other):
        """Attempts an equivalency match between two Reminders
        If a compared field in either Reminder is None, that field
        is ignored. The date the reminders were added is ignored.
        """
        for attrib in ('content', 'category', 'date_due'):
            self_attr = getattr(self, attrib)
            other_attr = getattr(other, attrib)

            if self_attr is None or other_attr is None:
                continue
            elif self_attr != other_attr:
                return False

        return True

    def __str__(self):
        string = "{category}: #{serial} - {content}"
        if self.date_due:
            string += " (Due: {date_due})"

        return string.format(**self.__dict__)

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


class InvalidSerialException(Exception):
    pass


class DatabaseDoesNotExistException(Exception):
    pass


# Implementation details
def _confirm():
    """Handles user input for confirming various questions
    Allows Trivial Todo to work with both Python 2 & 3
    """
    prompt = "(y/N) "
    if sys.version_info.major == 3:
        inpt = input(prompt)
    else:
        inpt = raw_input(prompt)

    return inpt.lower() in ('y', 'yes')


def _load_reminders(stream=None):
    """Shortcut for loading the shelve with a context manager"""
    # Necessary to reload stream for testing purposes
    if stream is None:
        stream = DB_LOCATION
    return closing(shelve.open(stream))


def _iter_reminders():
    """Privides an iterator for all of the reminders"""
    with _load_reminders() as reminders:
        categories = (reminders[x] for x in reminders.keys() if x != 'serial')
        for reminder in chain(*categories):
            yield reminder


def _append_reminder(reminder):
    """Necessary to prevent writeback being required on the shelve"""
    with _load_reminders() as reminders:
        temp = reminders.get(reminder.category, [])
        temp.append(reminder)
        reminders[reminder.category] = temp


def _remove_reminder(reminder):
    """Necessary to prevent writeback being required on the shelve"""
    with _load_reminders() as reminders:
        temp = reminders.get(reminder.category, [])
        temp.remove(reminder)
        if not temp:
            del reminders[reminder.category]
        else:
            reminders[reminder.category] = temp


def _parse_absolute_date(date, sep):
    """Helper function that handles parsing relative times like '03/08'"""
    def convert(day, month, year):
        try:
            return datetime.date(year, month, day)
        except ValueError:
            day, month = month, day

        try:
            return datetime.date(year, month, day)
        except ValueError:
            raise InvalidDateException("Cannot parse time: {}".format(date))

    if date.count(sep) == 1:
        month, day = date.split(sep)
        year = datetime.date.today().year
        return convert(int(day), int(month), year)

    elif date.count(sep) == 2:
        date_list = [int(x) for x in date.split(sep)]
        year = max(date_list)
        date_list.remove(year)
        month, day = date_list
        return convert(day, month, year)

    else:
        raise InvalidDateException("Cannot parse time: {}".format(date))


def _parse_relative_date(date):
    """Helper function that handles parsing relative times like '2 weeks'"""
    relative = {'days': datetime.timedelta(days=1),
                'weeks': datetime.timedelta(days=7)}
    try:
        number, time = date.split()
        # Handle things like '1 day' which should be 'tomorrow', but meh
        if time + 's' in relative:
            time += 's'
        if time in relative:
            return datetime.date.today() + (int(number) * relative[time])
    except ValueError:
        raise InvalidDateException("Cannot parse time: {}".format(date))

    raise InvalidDateException("Cannot parse time: {}".format(date))


def _print_results(results):
    """Helper function used to display results"""
    if isinstance(results, Reminder):
        print(results)
        return None
    elif len(results) == 1:
        print(results[0])
        return None

    categories = {}
    for result in results:
        categories.setdefault(result.category, []).append(result)

    for category, lst in categories.items():
        print("{}:".format(category))
        for reminder in lst:
            string = "\t#{serial} - {content}"

            if reminder.date_due:
                string += " ({date_due})"

            print(string.format(**reminder.__dict__))


def _create_new_database(path):
    """Used when specified shelve database does not exist"""
    print("Database at '{}' does not exist, create it?".format(path))
    if _confirm():
        return True
    raise DatabaseDoesNotExistException("Specified database does not exist")


# Workhorse functions called by argument functions
def search_field(target, field):
    """Returns all matching reminders based on a given field and target data
    Returns a list of matches
    """
    matches = []

    for reminder in _iter_reminders():
        if target == getattr(reminder, field):
            matches.append(reminder)

    if not matches:
        raise ReminderDoesNotExistException("Could not find matching reminder")

    return matches


def search_in_content(content, case_insensitive=False):
    """Searches for reminders by partial content
    Returns a list of all matches. Optional parameter for case insensitivity.
    Case sensitive by default.
    """
    matches = []

    if case_insensitive:
        target = content.lower()
    else:
        target = content

    for reminder in _iter_reminders():
        if case_insensitive:
            search = reminder.content.lower()
        else:
            search = reminder.content

        if target in search:
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
        raise ReminderDoesNotExistException(
            "The reminder that you're attempting to remove does not exist.")

    _remove_reminder(reminder)


def parse_date(date):
    """Parses date strings such as 'tomorrow' or '03/08' to valid datetime"""
    trans = {'today': datetime.date.today(),
             'tomorrow': datetime.date.today() + datetime.timedelta(days=1)}

    if date in trans:
        return trans[date]

    if '/' in date:
        return _parse_absolute_date(date, '/')
    elif '.' in date:
        return _parse_absolute_date(date, '.')
    elif '-' in date:
        return _parse_absolute_date(date, '-')
    elif ' ' in date:
        return _parse_relative_date(date)

    raise InvalidDateException("Cannot parse time: {}".format(date))


# Argument functions called depending on subparser used
def add(args):
    """Called by the 'add' subparser"""
    arguments = {}

    if not args.content:
        content = tempfile.mktemp()
        subprocess.call([os.getenv('EDITOR'), content])
        with open(content) as text:
            arguments['content'] = '\n'.join(text.readlines()).strip()
    else:
        arguments['content'] = args.content

    if args.date_due:
        arguments['date_due'] = parse_date(args.date_due)
    if args.category:
        arguments['category'] = args.category

    reminder = Reminder(**arguments)
    add_reminder(reminder)
    print("Reminder added successfully")


def remove(args):
    """Called by the 'remove' subparser"""
    reminder = search_field(args.serial, 'serial')[0]
    if not args.confirm:
        print("Remove '{}'?".format(reminder))

    if args.confirm or _confirm():
        _remove_reminder(reminder)
        print("Reminder removed successfully")


def search(args):
    """Called by the 'search' subparser"""
    if args.content:
        reminders = search_in_content(args.content, args.insensitive)
    else:
        reminders = []

    if args.date_due and reminders:
        date = parse_date(args.date_due)
        matches = []

        for reminder in reminders:
            if not reminder.date_due:
                continue
            elif args.after and reminder.date_due >= date:
                matches.append(reminder)
            elif args.before and reminder.date_due <= date:
                matches.append(reminder)
            elif reminder.date_due == date:
                matches.append(reminder)

        return _print_results(matches)

    return _print_results(reminders)


def lst(args):
    """Called by the 'show' subparser"""
    if args.serial:
        try:
            return _print_results(search_field(args.serial, 'serial')[0])
        except ValueError:
            raise InvalidSerialException("{} is not a valid serial number")
    elif args.category:
        return _print_results(search_field(args.category, 'category'))
    else:
        return _print_results(list(_iter_reminders()))


def edit(args):
    content = tempfile.mktemp()
    reminder = search_field(args.serial, 'serial')[0]
    _remove_reminder(reminder)

    with open(content, 'w') as text:
        text.write(reminder.content)

    subprocess.call([os.getenv('EDITOR'), content])

    with open(content) as text:
        reminder.content = '\n'.join(text.readlines()).strip()

    _append_reminder(reminder)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="""Trivial Todo keeps track of your reminders. Remember to
        enclose multi-word arguments in quotes! For help on the sub commands,
        use todo COMMAND --help (eg. todo add --help)""",

        epilog="""Note on dates: Trivial todo allows dates to be entered in
        either absolute or relative form. Relative form appears as 'today',
        'tomorrow', or even '6 weeks'. Absolute form is in the order of month,
        day, year. Year is optional in absolute form and will use the current
        year if omitted. Either a period, dash or slash may be used (eg. 03/08
        or 03.08 or 03-08).""")

    parser.add_argument('--db', '-d', help="Use specified shelve database")

    subparsers = parser.add_subparsers(help="Commands for todo:")

    # Add reminders
    parser_add = subparsers.add_parser('add', help="add reminders")
    parser_add.add_argument('content', help="""text for your reminder. If
            omitted, your $EDITOR will be launched to produce the reminder
            content""", nargs='?', default=None)
    parser_add.add_argument('--category', '-c', help="""category of your
            reminder (default: 'general')""")
    parser_add.add_argument('--due', '-d', help="""due date for your reminder
            (default: None)""", dest='date_due')
    parser_add.set_defaults(func=add)

    # Remove reminders
    parser_remove = subparsers.add_parser('remove', help="""remove reminders
            by number""")
    parser_remove.add_argument('serial', help="""number of the reminder to be
            removed""", metavar='NUMBER', type=int)
    parser_remove.add_argument(
        '--yes', '-y', action='store_const',
        const=True, help="""bypasses request for approval before removing
        the reminder""", dest='confirm', default=None)
    parser_remove.set_defaults(func=remove)

    # Search reminders
    parser_search = subparsers.add_parser('search', help="search reminders")
    parser_search.add_argument('content', help="find reminders by content",
                               nargs='?', default=None)
    parser_search.add_argument(
        '--due', '-d', help="find reminders by due date",
        dest='date_due', default=None)
    parser_search.add_argument(
        '--before', '-b', help=("search for due dates prior to given date. "
                                "(if no date is given, this will be ignored)"),
        default=False, action='store_const', const=True)
    parser_search.add_argument(
        '--after', '-a', help=("search for due dates following given date. "
                               "(if no date is given, this will be ignored)"),
        default=False, action='store_const', const=True)
    parser_search.add_argument(
        '--ignore-case', '-i', help="case insensitive search",
        dest='insensitive', const=True, default=False, action='store_const')
    parser_search.set_defaults(func=search)

    # List reminders
    parser_list = subparsers.add_parser('list', help="list reminders")
    group = parser_list.add_mutually_exclusive_group()
    group.add_argument('--number', '-n', help="list a reminder by its number",
                       dest='serial', default=None, metavar='NUMBER', type=int)
    group.add_argument('--category', '-c', help="""list reminders in a
            category""", default=None)
    parser_list.set_defaults(func=lst)

    # Edit reminder
    parser_edit = subparsers.add_parser('edit', help="edit a reminder")
    parser_edit.add_argument('serial', help="""number of the reminder to be
            edited""", metavar='NUMBER', type=int)
    parser_edit.set_defaults(func=edit)

    args = parser.parse_args()

    if args.db:
        if not os.path.exists(args.db):
            _create_new_database(args.db)
        DB_LOCATION = args.db
    else:
        if not os.path.exists(DB_LOCATION):
            _create_new_database(DB_LOCATION)

    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()
