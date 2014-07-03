from django.test import TestCase
from django.test.client import RequestFactory

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
        self.success_msg = '{"text": "Entry was received. Thank you."}'
        self.second_error = "We've noticed that some information is still incorrect, but "\
                            "registered this patient. Please be sure to enter all information "\
                            "as listed on your instruction card"

    def make_request(self, data):
        """Make Test request with POST data."""
        request = self.factory.post('/clinics/visit/', data=data)
        return clinics.VisitView.as_view()(request)

    def test_visit(self):
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg)

    def test_visit_wrong_clinic(self):
        """Test that a wrong clinic is not registered"""
        reg_data = {'text': '2 08122233301 4001 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        error_msg = "Clinic number incorrect. Must be 1-11, please check your instruction card "\
            "and re-enter the entire patient code in 1 sms"
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

        # Test that it is not registered 1st time.
        self.assertEqual(0, models.Visit.objects.count())

    def test_two_wrong_clinic_entries(self):
        """Test that a wrong clinic is registered on second sms."""
        reg_data = {'text': '2 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        error_msg = "Clinic code does not seem correct, but patient was registered. Thank you."

        # Test that it is not registered 1st time.
        self.assertEqual(0, models.Visit.objects.count())

        # Test 2nd attempt message.
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

        # Test 2nd attempt is registered.
        self.assertEqual(1, models.Visit.objects.count())

        # Test that 3rd attempt message.
        response = self.make_request(reg_data)
        error_msg = "Clinic number incorrect. Must be 1-11, please check your instruction card "\
            "and re-enter the entire patient code in 1 sms"
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

    def test_wrong_right_wrong_clinic_entries(self):
        """Test that a right clinic entry after wrong entry clears the slate.

        1. wrong entry
        2. right entry
        3. wrong entry

        is equivalent to
        1. right entry
        2. wrong entry
        """
        # 1st entry. Clinic is wrong
        reg_data = {'text': '2 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)

        # 2nd entry, Clinic is right
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)

        # 3rd entry, Clinic is wrong
        reg_data = {'text': '2 08122233301 4001 5', 'phone': '+2348022112211'}
        error_msg = "Clinic number incorrect. Must be 1-11, please check your instruction card "\
            "and re-enter the entire patient code in 1 sms"
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

    def test_prioritize_mobile_error(self):
        """Test mobile and clinic are incorrect, prioritize mobile."""
        reg_data = {'text': '15 8122233301 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        error_msg = 'Mobile number incorrect for patient with serial 4000. Must be 11 digits '\
                    'with no spaces. Please check your '\
                    'instruction card and re-enter the entire patient code in 1 text.'
        self.assertEqual(response.content, json.dumps({"text": "%s" % error_msg}))

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

    def test_visit_registration(self):
        """Test that the registration works."""
        reg_data = {'text': '08122233301 4001 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid. Please retry"}')

    def test_visit_no_phone(self):
        """Test that the phone number of '1' will validate."""
        reg_data = {'text': '1 1 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg)

    def test_visit_wrong_clinic1(self):
        """Test that a non-numeric data is not registered."""
        reg_data = {'text': 'A 08122233301 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "Your message is invalid. Please retry"}')

    def test_invalid_mobile(self):
        """Test that a non 11-digit number is not registered."""
        reg_data = {'text': '1 8122233301 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        error_msg = 'Mobile number incorrect for patient with serial 4000. Must be 11 digits '\
                    'with no spaces. Please check your '\
                    'instruction card and re-enter the entire patient code in 1 text.'
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

        # Test second wrong sms same message
        response = self.make_request(reg_data)
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

    def test_visit_invalid_service(self):
        """Test that invalid service code gives correct message and registered."""
        reg_data = {'text': '1 08122233301 4000 3', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        error_msg = 'Service code does not seem correct, but patient was registered. Thank you.'
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

        # Test that it is registered.
        self.assertEqual(1, models.Visit.objects.count())

        # Test error is logged.
        self.assertEqual(1, models.VisitRegistrationErrorLog.objects.count())

    def test_visit_invalid_serial(self):
        """Test that invalid serial gives correct message and registered."""
        reg_data = {'text': '1 08122233301 400 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        error_msg = 'Serial number does not seem correct, but patient was registered. Thank you.'
        self.assertEqual(response.content, '{"text": "%s"}' % error_msg)

        # Test that it is registered.
        self.assertEqual(1, models.Visit.objects.count())

        # Test error is logged.
        self.assertEqual(1, models.VisitRegistrationErrorLog.objects.count())

    def test_save_visit(self):
        """Test that the visit information is saved."""
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        visit_count = models.Visit.objects.count()
        self.assertEqual(1, visit_count)


class TestFeedbackView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def make_request(self, data):
        """Make test request with POST data."""
        request = self.factory.post('/clinics/feedback/', data=data)
        return clinics.FeedbackView.as_view()(request)

    def test_feedback_status(self):
        """Test that feedback view returns status_code 200."""
        values = [
            {
                "category": "1",
                "time": "2014-07-02T07:38:37.490596Z",
                "text": "1",
                "rule_value": "1",
                "value": "1",
                "label": "number"
            },
            {
                "category": "All Responses",
                "time": "2014-07-02T07:38:37.510620Z",
                "text": "text",
                "rule_value": "text",
                "value": "text",
                "label": "text"
            }
        ]
        json_data = json.dumps(values)

        feedback = {
            "phone": ["+12065551212"],
            "values": json_data
            }
        response = self.make_request(feedback)
        self.assertEqual(200, response.status_code)

        # Test that data is saved.
        #self.assertEqual(1, models.GenericFeedback.objects.count())

    def test_feedback_saved(self):
        """Test that feedback is saved."""

    def test_feedback_noclinic_saved(self):
        """Test that feedback without clinic is saved with the clinic name
        in message field."""
