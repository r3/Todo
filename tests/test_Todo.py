import tempfile
import os
import shutil
import shelve
import todo
import pytest
import datetime

from contextlib import closing
from collections import namedtuple


class TestTodo():
    sample = None  # populated in TestTodo.setup_db

    # Setup/teardown/helper methods to be used in later tests
    def setup_db(self):
        name = os.path.join(tempfile.mkdtemp(), 'todo.shelve')
        setattr(todo, 'STREAM', name)

        TestTodo.sample = [todo.Reminder('reminder 1', 'activities'),
                           todo.Reminder('reminder 2', 'activities'),
                           todo.Reminder('reminder 3', 'activities')]

        with closing(shelve.open(name)) as db:
            db['activities'] = TestTodo.sample

        return name

    def teardown_db(self, db):
        path = os.path.dirname(db)
        shutil.rmtree(path)

    def pytest_funcarg__db(self, request):
        return request.cached_setup(self.setup_db, self.teardown_db,
                                    scope='class')

    def setup_reminder(self):
        return todo.Reminder('content', 'catagory', 'due_date', 'date')

    def pytest_funcarg__reminder(self, request):
        return request.cached_setup(self.setup_reminder, scope='class')

    # Test basic backend methods
    def test_proper_setup(self, db):
        with closing(shelve.open(db)) as reminders:
            assert len(reminders['activities']) == 3

    def test_append_reminder(self, db, reminder):
        todo._append_reminder(reminder)

        with closing(shelve.open(db)) as reminders:
            assert reminders['catagory'] == [reminder]

    def test_retrieve_serial(self, db, reminder):
        assert todo.search_field(4, 'serial')[0] == reminder

    def test_remove_reminder(self, db, reminder):
        todo._remove_reminder(reminder)

        with pytest.raises(KeyError):
            with closing(shelve.open(db)) as reminders:
                assert reminders['catagory'] == None

    def test_iter_reminders(self, db):
        assert list(todo._iter_reminders()) == TestTodo.sample

    def test_serial(self, reminder):
        assert reminder.serial == 4

    # Test backend methods
    def test_search_field(self):
        assert todo.search_field('reminder 1', 'content')[0] == TestTodo.sample[0]

    def test_search_in_content(self):
        assert todo.search_in_content('reminder') == TestTodo.sample

    def test_reminder_exists_True(self, reminder):
        assert todo.reminder_exists(TestTodo.sample[0])

    def test_reminder_exists_False(self):
        reminder = todo.Reminder('New Reminder')
        assert todo.reminder_exists(reminder) == False

    def test_add_existing_reminder(self):
        with pytest.raises(todo.ReminderExistsException):
            todo.add_reminder(TestTodo.sample[0])

    def test_add_new_reminder(self):
        reminder = todo.Reminder('This should not clash')
        todo.add_reminder(reminder)
        assert todo.reminder_exists(reminder)

    def test_delete_fake_reminder(self):
        reminder = todo.Reminder('This is a new reminder')
        with pytest.raises(todo.ReminderDoesNotExistException):
            todo.delete_reminder(reminder)

    def test_delete_real_reminder(self, reminder):
        todo.add_reminder(reminder)
        todo.delete_reminder(reminder)
        assert todo.reminder_exists(reminder) == False

    # Test time translation
    def test_time_parse_tomorrow(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        assert todo.parse_date('tomorrow') == tomorrow

    def test_time_parse_today(self):
        today = datetime.date.today()
        assert todo.parse_date('today') == today

    def test_time_parse_day(self):
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        assert todo.parse_date('1 day') == tomorrow

    def test_time_parse_week(self):
        week = datetime.date.today() + datetime.timedelta(days=7)
        assert todo.parse_date('1 week') == week

    def test_time_parse_5_days(self):
        five_days = datetime.date.today() + datetime.timedelta(days=5)
        assert todo.parse_date('5 days') == five_days

    def test_time_parse_5_weeks(self):
        five_weeks = datetime.date.today() + (5 * datetime.timedelta(days=7))
        assert todo.parse_date('5 weeks') == five_weeks

    def test_time_parse_fail(self):
        with pytest.raises(todo.InvalidDateException):
            todo.parse_date('Parse This!')

    # Test subparser methods
    def test_add_content(self):
        args = {'content': "This is my reminder content", 'catagory': None,
                'date_due': None, 'date': None}
        Namespace = namedtuple('Namespace', args)
        reminder = todo.Reminder(**args)
        todo.add(Namespace(**args))
        assert todo.reminder_exists(reminder)

    #def test_add_content_and_catagory(self, args_add):
        #arguments = args("Another reminder", 'catagory', None, None)
        #reminder = todo.Reminder(**arguments)
        #todo.add(arguments)
        #assert todo.reminder_exists(reminder)

    #def test_add_content_and_due(self, args_add):
        #arguments = args("More content", None, 'tomorrow', None)
        #reminder = todo.Reminder(**arguments)
        #todo.add(arguments)
        #assert todo.reminder_exists(reminder)

    #def test_add_content_catagory_and_due(self, args_add):
        #arguments = args("All three, baby", 'catagory', '11/6', None)
        #reminder = todo.reminder(**arguments)
        #todo.add(arguments)
        #assert todo.reminder_exists(reminder)
