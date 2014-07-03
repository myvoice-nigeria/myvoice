import datetime
import mock

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from myvoice.core.tests import factories

from .. import models
from .. import statistics


class TestClinic(TestCase):
    Model = models.Clinic
    Factory = factories.Clinic

    def test_unicode(self):
        """Smoke test for Clinic string representation."""
        obj = self.Factory.create(name='Hello')
        self.assertEqual(str(obj), 'Hello')


class TestClinicStaff(TestCase):
    Model = models.ClinicStaff
    Factory = factories.ClinicStaff

    def test_unicode(self):
        """Smoke test for ClinicStaff string representation."""
        obj = self.Factory.create(name='Hello')
        self.assertEqual(str(obj), 'Hello')

    def test_get_name_display_user(self):
        """User name should be preferred to 'name' field on a staff member."""
        obj = self.Factory.create(
            user=factories.User(first_name='a', last_name='b'),
            name='hello')
        self.assertEqual(obj.get_name_display(), 'a b')

    def test_get_name_display_no_user(self):
        """If staff member has no associated user, 'name' field should be used."""
        obj = self.Factory.create(name='hello')
        self.assertEqual(obj.get_name_display(), 'hello')


class TestService(TestCase):
    Model = models.Service
    Factory = factories.Service

    def test_unicode(self):
        obj = self.Factory.create(name='hello')
        self.assertEqual(str(obj), 'hello')


class TestPatient(TestCase):
    Model = models.Patient
    Factory = factories.Patient

    def test_unicode(self):
        """Smoke test for Patient string representation."""
        obj = self.Factory.create(name='test')
        self.assertEqual(str(obj), 'test')

    def test_get_name_display(self):
        """Contact name should be preferred to 'name' field on patient."""
        obj = self.Factory.create(
            name='test',
            contact=factories.Contact(name='test contact'))
        self.assertEqual(obj.get_name_display(), "test contact")

    def test_get_name_no_contact(self):
        """Show name if no contact attached to patient."""
        obj = self.Factory.create(name='test')
        self.assertEqual(obj.get_name_display(), 'test')


class TestVisit(TestCase):
    Model = models.Visit
    Factory = factories.Visit

    def test_unicode(self):
        """Smoke test for Visit string representation."""
        obj = self.Factory.create(
            patient=factories.Patient(name='test_patient'),
            service=factories.Service(name='test_service'))
        self.assertEqual(str(obj), 'test_patient')


class TestClinicStatistic(TestCase):
    Model = models.ClinicStatistic
    Factory = factories.ClinicStatistic

    def test_unicode(self):
        """Smoke test for ClinicStatistic string representation."""
        obj = self.Factory.create(
            clinic__name='Hello',
            month=datetime.date(2012, 10, 1),
            statistic=statistics.INCOME)
        self.assertEqual(str(obj), 'Income for Hello for October 2012')

    def test_get_month_display(self):
        """Smoke test for month display method."""
        obj = self.Factory.create(month=datetime.date(2012, 10, 1))
        result = obj.get_month_display()
        self.assertEqual(result, 'October 2012')

    def test_get_month_display_custom(self):
        """Smoke test for month display method."""
        obj = self.Factory.create(month=datetime.date(2012, 10, 1))
        result = obj.get_month_display('%d %b %Y')
        self.assertEqual(result, '01 Oct 2012')

    def test_unique_statistic_for_clinic_and_month(self):
        obj = self.Factory.create()
        with self.assertRaises(IntegrityError):
            self.Factory.create(statistic=obj.statistic, clinic=obj.clinic,
                                month=obj.month)

    @mock.patch.object(models.ClinicStatistic, 'get_statistic_type')
    def test_no_value(self, get_statistic_type):
        for statistic_type in [statistics.INTEGER, statistics.FLOAT,
                               statistics.PERCENTAGE, statistics.TEXT]:
            get_statistic_type.return_value = statistics.INTEGER
            obj = self.Model(clinic=factories.Clinic(), month=datetime.date(2012, 10, 1))
            self.assertEqual(obj.int_value, None)
            self.assertEqual(obj.float_value, None)
            self.assertEqual(obj.text_value, None)
            self.assertEqual(obj.value, None)
            self.assertRaises(ValidationError, obj.clean_value)

    @mock.patch.object(models.ClinicStatistic, 'get_statistic_type')
    def test_statistic_int(self, get_statistic_type):
        # Manually construct object to have more control over statistic type.
        get_statistic_type.return_value = statistics.INTEGER
        obj = self.Model(clinic=factories.Clinic(), month=datetime.date(2012, 10, 1))

        # Value in float_value should not validate.
        obj.float_value = 1
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Value in text_value should not validate.
        obj.text_value = '1'
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Non-integer value should not validate.
        obj.int_value = 'non-integer'
        self.assertEqual(obj.value, 'non-integer')
        self.assertRaises(ValidationError, obj.clean_value)

        # Manually set value.
        obj.int_value = 1
        self.assertEqual(obj.value, 1)
        obj.clean_value()
        obj.int_value = None  # reset

        # Use property to set value.
        obj.value = 1
        self.assertEqual(obj.int_value, 1)
        self.assertEqual(obj.float_value, None)
        self.assertEqual(obj.text_value, None)
        self.assertEqual(obj.value, 1)
        obj.clean_value()

        # Should be able to retrieve value after storing in database.
        obj.save()
        obj = self.Model.objects.get(pk=obj.pk)
        self.assertEqual(obj.value, 1)

    @mock.patch.object(models.ClinicStatistic, 'get_statistic_type')
    def test_statistic_float(self, get_statistic_type):
        # Manually construct object to have more control over statistic type.
        get_statistic_type.return_value = statistics.FLOAT
        obj = self.Model(clinic=factories.Clinic(), month=datetime.date(2012, 10, 1))

        # Value in int_value should not validate.
        obj.int_value = 1
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Value in text_value should not validate.
        obj.text_value = '1.5'
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Non-float value should not validate.
        obj.float_value = 'non-float'
        self.assertEqual(obj.value, 'non-float')
        self.assertRaises(ValidationError, obj.clean_value)

        # Manually set value.
        obj.float_value = 1.5
        self.assertEqual(obj.value, 1.5)
        obj.clean_value()
        obj.float_value = None  # reset

        # Use property to set value.
        obj.value = 1.5
        self.assertEqual(obj.float_value, 1.5)
        self.assertEqual(obj.int_value, None)
        self.assertEqual(obj.text_value, None)
        self.assertEqual(obj.value, 1.5)
        obj.clean_value()

        # Should be able to retrieve value after storing in database.
        obj.save()
        obj = self.Model.objects.get(pk=obj.pk)
        self.assertEqual(obj.value, 1.5)

    @mock.patch.object(models.ClinicStatistic, 'get_statistic_type')
    def test_statistic_percentage(self, get_statistic_type):
        # Manually construct object to have more control over statistic type.
        get_statistic_type.return_value = statistics.PERCENTAGE
        obj = self.Model(clinic=factories.Clinic(), month=datetime.date(2012, 10, 1))

        # Value in int_value should not validate.
        obj.int_value = 1
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Value in text_value should not validate.
        obj.text_value = '1.5'
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Non-float value should not validate.
        obj.float_value = 'non-float'
        self.assertEqual(obj.value, 'non-float')
        self.assertRaises(ValidationError, obj.clean_value)

        # Manually set value.
        obj.float_value = 1.5
        self.assertEqual(obj.value, 1.5)
        obj.clean_value()
        obj.float_value = None  # reset

        # Use property to set value.
        obj.value = 1.5
        self.assertEqual(obj.float_value, 1.5)
        self.assertEqual(obj.int_value, None)
        self.assertEqual(obj.text_value, None)
        self.assertEqual(obj.value, 1.5)
        obj.clean_value()

        # Should be able to retrieve value after storing in database.
        obj.save()
        obj = self.Model.objects.get(pk=obj.pk)
        self.assertEqual(obj.value, 1.5)

    @mock.patch.object(models.ClinicStatistic, 'get_statistic_type')
    def test_statistic_text(self, get_statistic_type):
        # Manually construct object to have more control over statistic type.
        get_statistic_type.return_value = statistics.TEXT
        obj = self.Model(clinic=factories.Clinic(), month=datetime.date(2012, 10, 1))

        # Value in int_value should not validate.
        obj.int_value = 1
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Value in float_value should not validate.
        obj.float_value = 1.5
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Null value should not validate.
        obj.text_value = None
        self.assertEqual(obj.value, None)
        self.assertRaises(ValidationError, obj.clean_value)

        # Manually set value.
        obj.text_value = 'hello'
        self.assertEqual(obj.value, 'hello')
        obj.clean_value()
        obj.text_value = None  # reset

        # Use property to set value.
        obj.value = 'hello'
        self.assertEqual(obj.float_value, None)
        self.assertEqual(obj.int_value, None)
        self.assertEqual(obj.text_value, 'hello')
        self.assertEqual(obj.value, 'hello')
        obj.clean_value()

        # Should be able to retrieve value after storing in database.
        obj.save()
        obj = self.Model.objects.get(pk=obj.pk)
        self.assertEqual(obj.value, 'hello')
