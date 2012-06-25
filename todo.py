import shelve
import datetime

from contextlib import closing

STREAM = 'todo.shelve'


class Reminder():
    """A reminder unit with a date, optional due date, catagory, and content"""
    def __init__(self, content=None, catagory=None, date_due=None, date=None):
        self.serial = Reminder.next_serial()
        self.date = date if date else datetime.datetime.now()
        self.content = content
        self.catagory = catagory
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


def _load_reminders(stream=STREAM):
    return closing(shelve.open(stream))


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
