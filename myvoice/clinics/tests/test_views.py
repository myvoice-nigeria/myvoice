from django.test import TestCase
from django.test.client import RequestFactory

#import mock
import json

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
        error_msg = "Clinic number incorrect. Must be 1-11, please check your instruction card "\
            "and re-enter the entire patient code in 1 sms"
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

    def test_multiple_fields_incorrect(self):
        """Test multiple fields are incorrect."""
        reg_data = {
            'text': '15 8122356701 4000 5'
        }
        response = self.make_request(reg_data)
        error_msg = "Some of the fields you have entered are incorrect. This patient has not "\
                    "been registered.  Must be a number 1 - 5 please check your instruction "\
                    "card and re-enter the entire patient code in 1 text."
        self.assertEqual(response.content, json.dumps({"text": "%s" % error_msg}))

    def test_visit_registration(self):
        """Test that the registration works."""
        reg_data = {
            'text': '08122356701 4001 5'
        }
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid. Please retry"}')

    def test_visit_no_phone(self):
        """Test that the phone number of '1' will validate."""
        reg_data = {'text': '1 1 4000 5'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Thank you for registering"}')

    def test_visit_non_numeric_data(self):
        """Test that a non-numeric data is not registered."""
        reg_data = {'text': 'A 08122356701 4000 5'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid. Please retry"}')

    def test_invalid_phone(self):
        """Test that a non 11-digit number is not registered."""
        reg_data = {'text': '1 8122356701 4000 5'}
        response = self.make_request(reg_data)
        error_msg = 'Mobile number incorrect. Must be 11 digits with no spaces. Please check your '\
                    'instruction card and re-enter the entire patient code in 1 text.'
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

    def test_visit_invalid_service(self):
        """Test that invalid service code is not registered."""
        reg_data = {'text': '1 08122356701 4005 3'}
        response = self.make_request(reg_data)
        error_msg = 'Service code incorrect. Must be a number 1 - 5 please check your '\
                    'instruction card and re-enter the entire patient code in 1 text.'
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

    def test_save_visit(self):
        """Test that the visit information is saved."""
        reg_data = {
            'text': '1 08122356701 4001 5',
            'phone': '+2348022112211'
        }
        self.make_request(reg_data)
        visit_count = models.Visit.objects.count()
        self.assertEqual(1, visit_count)
