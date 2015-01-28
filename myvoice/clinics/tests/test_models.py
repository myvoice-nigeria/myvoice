from django.test import TestCase

from myvoice.core.tests import factories

from .. import models


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
        obj = self.Factory.create(serial=5, clinic__name='Hello')
        self.assertEqual(str(obj), '5 at Hello')


class TestVisit(TestCase):
    Model = models.Visit
    Factory = factories.Visit

    def test_unicode(self):
        """Smoke test for Visit string representation."""
        obj = self.Factory.create(
            patient=factories.Patient(serial=5, clinic__name='Hello'),
            service=factories.Service(name='test_service'))
        self.assertEqual(str(obj), '5 at Hello')


class TestManualRegistration(TestCase):

    Model = models.ManualRegistration
    Factory = factories.ManualRegistration

    def test_unicode(self):
        """Smoke test for ManualRegistration string representation."""
        obj = self.Factory.create(
            clinic=factories.Clinic(name="hello"),
            visit_count=10)
        self.assertEqual(str(obj), 'hello')


class TestGenericFeedback(TestCase):
    Model = models.GenericFeedback
    Factory = factories.GenericFeedback

    def test_unicode(self):
        """Smoke test for Generic Feedback string representation."""
        obj = self.Factory.create(
            clinic=factories.Clinic(name='text_clinic'),
            sender='234811111111')
        self.assertEqual(str(obj), '234811111111')


class TestClinicScore(TestCase):
    Model = models.ClinicScore
    Factory = factories.ClinicScore

    def test_unicode(self):
        """Smoke test for Clinic Score string representation."""
        obj = self.Factory.create(
            clinic=factories.Clinic.create(name='test_clinic'))
        self.assertEqual(str(obj), 'test_clinic')
