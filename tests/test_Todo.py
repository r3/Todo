import tempfile
import os
import shutil
import shelve
import todo

from contextlib import closing


class TestTodo():
    def setup_db(self):
        name = os.path.join(tempfile.mkdtemp(), 'todo.shelve')
        todo.STREAM = name

        with closing(shelve.open(name)) as db:
            db['serial'] = 0
            db['activities'] = [todo.reminder('reminder 1', 'activities'),
                                todo.reminder('reminder 2', 'activities'),
                                todo.reminder('reminder 3', 'activities')]

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
        return request.cached_setup(self.setup_db, scope='class')

    def test_serial(self, reminder):
        assert reminder.serial == 4

    def test_append_reminder(self, db, reminder):
        todo._append_reminder(reminder)

        with closing(shelve.open(db)) as reminders:
            assert reminders['catagory'] == [reminder]

    def test_retrieve_serial(self, db, reminder):
        assert todo.retrieve_serial(reminder) == 4

    def test_remove_reminder(self, db, reminder):
        todo._remove_reminder(reminder)

        with closing(shelve.open(db)) as reminders:
            assert reminders['catagory'] == None
