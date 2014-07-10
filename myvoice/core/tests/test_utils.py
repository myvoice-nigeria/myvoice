import datetime
import mock

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


class TestCSVExport(TestCase):

    def setUp(self):
        self.qset = mock.MagicMock()
        self.row1 = mock.Mock()
        self.row1.name = 'me'
        self.row1.address = 'somewhere'
        self.row1.counter = 5

        self.row2 = mock.Mock()
        self.row2.name = 'you'
        self.row2.address = 'elsewhere'
        self.row2.counter = 17

        self.header = ['name', 'address', 'counter']

        def side_effect():
            for row in [self.row1, self.row2]:
                yield row

        self.qset.__iter__.side_effect = side_effect

    def test_extract_qset_headers(self):
        """Test that we can get the headers of the qset."""
        data = utils.extract_qset_data(self.qset, self.header)
        header = data[0]
        self.assertEqual(['name', 'address', 'counter'], header)
        self.assertTrue(self.qset.assert_called_once())

    def test_extract_qset_data(self):
        """Test that we can get the data from the qset."""
        data = utils.extract_qset_data(self.qset, self.header)
        self.assertEqual(['me', 'somewhere', '5'], data[1])
        self.assertEqual(['you', 'elsewhere', '17'], data[2])
