from django.test import TestCase
from django.test.client import RequestFactory

#import mock

from myvoice.core.tests import factories

from myvoice.clinics import views as clinics
from myvoice.clinics import models


class TestVisitView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.clinic = factories.Clinic.create(code=1)
        self.service = factories.Service.create(code=5)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)

    def make_request(self, data):
        """Make Test request with POST data"""
        request = self.factory.post('/views/registration/', data=data)
        return clinics.VisitView.as_view()(request)
        #return clinics.visit(request)

    def test_visit(self):
        reg_data = {
            'text': '1 08122356701 4001 5',
            'phone': '+2348022112211'
        }
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Thank you for registering"}')

    def test_visit_wrong_clinic(self):
        """Test that a wrong clinic is not registered"""
        reg_data = {
            'text': '2 08122356701 4001 5'
        }
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid, please retry"}')

    def test_visit_parts(self):
        """Test that the message must be of 4 parts."""
        reg_data = {
            'text': '08122356701 4001 3'
        }
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid, please retry"}')

    def test_visit_no_phone(self):
        """Test that the phone number of '1' will validate."""
        reg_data = {'text': '1 1 4000 5'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Thank you for registering"}')

    def test_visit_invalid_clinic_code(self):
        """Test that a non-numeric clinic is not registered."""
        reg_data = {'text': 'A 08122356701 4000 3'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid, please retry"}')

    def test_invalid_phone(self):
        """Test that a non 11-digit number is not registered."""
        reg_data = {'text': '1 8122356701 4000 3'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid, please retry"}')

    def test_visit_invalid_serial(self):
        """Test that invalid serial is not registered."""
        reg_data = {'text': '1 08122356701 4005 3'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid, please retry"}')

    def test_save_visit(self):
        """Test that the visit information is saved."""
        reg_data = {
            'text': '1 08122356701 4001 5',
            'phone': '+2348022112211'
        }
        self.make_request(reg_data)
        visit_count = models.Visit.objects.count()
        self.assertEqual(1, visit_count)
