import datetime
import mock

from django.test import TestCase
from django.utils import timezone

from .. import utils


class TestUtils(TestCase):

    def aware(self, dt):
        return timezone.make_aware(dt, timezone.utc)

    def setUp(self):
        self.dt = self.aware(timezone.datetime(2014, 7, 7))
        #self.dt = timezone.make_aware(timezone.datetime(2014, 7, 7), timezone.utc)
        #self.dt = datetime.datetime(2014, 7, 9)

    def test_get_week_start(self):
        """Test that it gets the start of the week."""
        week_start = utils.get_week_start(self.dt)
        self.assertEqual(self.aware(datetime.datetime(2014, 7, 7)), week_start)

    def test_get_week_end(self):
        """Test that it gets the end of the week."""
        week_end = utils.get_week_end(self.dt)
        self.assertEqual(self.aware(
            datetime.datetime(2014, 7, 13, 23, 59, 59, 999999)), week_end)

    def test_make_percentage(self):
        """Test that it gives correct percentage to 0 decimal places."""
        percentage = utils.make_percentage(50, 100, 0)
        self.assertEqual(50, percentage)

    def test_make_percentage_small(self):
        """Test that it works for small percentages."""
        percentage = utils.make_percentage(1, 10000, 2)
        self.assertEqual(0.01, percentage)

    def test_get_date(self):
        """Test that we can parse date string properly."""
        self.assertEqual(self.dt, utils.get_date('July 07, 2014'))


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

    def test_extract_no_name(self):
        """Test that extract_attr returns None with empty name."""
        obj = mock.Mock()
        obj.name = 'test'
        data = utils.extract_attr(obj, '')
        self.assertEqual(None, data)

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

    def test_extract_callable(self):
        """Test that a callable attribute is evaluated."""
        self.row1.name = lambda: "Hello"
        header = ['name']
        data = utils.extract_qset_data(self.qset, header)
        self.assertEqual(['Hello'], data[1])
        self.assertEqual(['you'], data[2])

    def test_extract_multilevel_callable(self):
        """Test that we can go through multiple levels of callable attributes."""
        child1 = mock.Mock()
        child1.name = lambda: "Child 1"  # row1.parent.child().name()
        child2 = mock.Mock()
        child2.name = lambda: "Child 2"  # row2.parent.child().name()
        self.row1.parent = mock.NonCallableMock()
        self.row1.parent.child = lambda: child1
        self.row2.parent = mock.NonCallableMock()
        self.row2.parent.child = lambda: child2
        header = ['parent.child.name']
        data = utils.extract_qset_data(self.qset, header)
        self.assertEqual(['Child 1'], data[1])
        self.assertEqual(['Child 2'], data[2])

    def test_extract_fk(self):
        """Test that we can get attributes of a fk field using dot notation."""
        self.row1.parent = mock.NonCallableMock()
        self.row1.parent.name = 'parent 1'
        self.row2.parent = mock.NonCallableMock()
        self.row2.parent.name = 'parent 2'
        header = ['name', 'address', 'counter', 'parent.name']
        data = utils.extract_qset_data(self.qset, header)
        self.assertEqual(['me', 'somewhere', '5', 'parent 1'], data[1])
        self.assertEqual(['you', 'elsewhere', '17', 'parent 2'], data[2])

    def test_extract_fk_header(self):
        """Test that header of fk attribute is space-separated."""
        self.row1.parent.name = 'parent 1'
        self.row2.parent.name = 'parent 2'
        header = ['name', 'address', 'counter', 'parent.name']
        data = utils.extract_qset_data(self.qset, header)
        self.assertEqual(['name', 'address', 'counter', 'parent name'], data[0])
