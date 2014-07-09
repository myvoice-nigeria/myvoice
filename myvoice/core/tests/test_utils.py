import datetime

from django.test import TestCase

from .. import utils


class TestUtils(TestCase):

    def setUp(self):
        self.dt = datetime.datetime(2014, 7, 9)

    def test_get_week_start(self):
        """Test that it gets the start of the week."""
        week_start = utils.get_week_start(self.dt)
        self.assertEqual(datetime.datetime(2014, 7, 7), week_start)

    def test_get_week_end(self):
        """Test that it gets the end of the week."""
        week_end = utils.get_week_end(self.dt)
        self.assertEqual(datetime.datetime(2014, 7, 13, 23, 59, 59, 999999), week_end)

    def test_make_percentage(self):
        """Test that it gives correct percentage to 0 decimal places."""
        percentage = utils.make_percentage(50, 100, 0)
        self.assertEqual(50, percentage)

    def test_make_percentage_small(self):
        """Test that it works for small percentages."""
        percentage = utils.make_percentage(1, 10000, 2)
        self.assertEqual(0.01, percentage)
