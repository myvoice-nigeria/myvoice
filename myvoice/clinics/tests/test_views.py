from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

import json
import datetime
import pytz

from myvoice.core.tests import factories

from myvoice.clinics import views as clinics
from myvoice.clinics import models
from myvoice.survey import models as survey_models


class TestVisitView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.clinic = factories.Clinic.create(code=1)
        self.service = factories.Service.create(code=5)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)
        self.invalid_msg = '{"text": "1 or more parts of your entry are missing, please check '\
                           'and enter the registration again."}'
        self.error_msg = '{"text": "Error for serial %s. There was a mistake in entering '\
                         '%s. Please check and enter the whole registration code again."}'
        self.success_msg = '{"text": "Entry received for patient with serial number %s. '\
                           'Thank you."}'

    def make_request(self, data):
        """Make Test request with POST data."""
        request = self.factory.post('/clinics/visit/', data=data)
        return clinics.VisitView.as_view()(request)

    def test_visit(self):
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.success_msg % 4001
        self.assertEqual(response.content, msg)

    def test_wrong_clinic(self):
        """Test that a wrong clinic is not registered"""
        reg_data = {'text': '2 08122233301 4001 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.error_msg % (4001, 'CLINIC')
        self.assertEqual(response.content, msg)

        # Test that it is not registered 1st time.
        self.assertEqual(0, models.Visit.objects.count())

    def test_two_wrong_clinic_entries(self):
        """Test that a wrong clinic is registered on second sms."""
        reg_data = {'text': '2 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        msg = self.error_msg % (4001, 'CLINIC')

        # Test that it is not registered 1st time.
        self.assertEqual(0, models.Visit.objects.count())

        # Test 2nd attempt message.
        response = self.make_request(reg_data)
        self.assertEqual(response.content, msg)

        # Test 2nd attempt is not registered.
        self.assertEqual(0, models.Visit.objects.count())

        # Test that 3rd attempt gives success message
        response = self.make_request(reg_data)
        msg = self.success_msg % 4001
        self.assertEqual(response.content, msg)

        # Test 3rd attempt is registered
        self.assertEqual(1, models.Visit.objects.count())

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
        msg = self.error_msg % (4001, 'CLINIC')
        response = self.make_request(reg_data)
        self.assertEqual(response.content, msg)

    def test_multiple_invalid_entries(self):
        """Test mobile and clinic are incorrect, prioritize mobile."""
        reg_data = {'text': '15 8122233301 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.error_msg % (4000, 'MOBILE, CLINIC')
        self.assertEqual(response.content, msg)

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

    def test_incomplete_entries(self):
        """Test that incomplete fields gives correct error message."""
        reg_data = {'text': '08122233301 4001 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.invalid_msg)

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

    def test_alpha_clinic_number(self):
        """Test that a non-numeric data is not registered."""
        reg_data = {'text': 'A 08122233301 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.invalid_msg)

    def test_no_mobile(self):
        """Test that the phone number of '1' will validate."""
        reg_data = {'text': '1 1 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.success_msg % 4000
        self.assertEqual(response.content, msg)

    def test_invalid_mobile(self):
        """Test that a non 11-digit number is not registered,
        even after 2 wrong entries."""
        reg_data = {'text': '1 8122233301 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.error_msg % (4000, 'MOBILE')
        self.assertEqual(response.content, msg)

        # Test second wrong sms same message
        response = self.make_request(reg_data)
        self.assertEqual(response.content, msg)

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

        # Test 3rd wrong sms not registered.
        response = self.make_request(reg_data)
        self.assertEqual(response.content, msg)

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

    def test_invalid_service(self):
        """Test that invalid service code gives correct message and registered."""
        reg_data = {'text': '1 08122233301 4000 3', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.error_msg % (4000, 'SERVICE')
        self.assertEqual(response.content, msg)

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

        # Test error is logged.
        self.assertEqual(1, models.VisitRegistrationError.objects.count())

    def test_3digit_serial(self):
        """Test that 3-digit serial is valid."""
        reg_data = {'text': '1 08122233301 400 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.success_msg % 400
        self.assertEqual(response.content, msg)

        # Test that it is registered.
        self.assertEqual(1, models.Visit.objects.count())

        # Test error is not logged.
        self.assertEqual(0, models.VisitRegistrationErrorLog.objects.count())

    def test_invalid_serial(self):
        """Test that invalid serial gives correct message and is not registered."""
        reg_data = {'text': '1 08122233301 40 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        msg = self.error_msg % (40, 'SERIAL')
        self.assertEqual(response.content, msg)

        # Test that it is not registered.
        self.assertEqual(0, models.Visit.objects.count())

        # Test error is logged.
        self.assertEqual(1, models.VisitRegistrationError.objects.count())

    def test_save_visit(self):
        """Test that the visit information is saved."""
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        visit_count = models.Visit.objects.count()
        self.assertEqual(1, visit_count)

    def test_save_mobile(self):
        """Test that mobile number is saved in Visit model."""
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        obj = models.Visit.objects.all()[0]
        self.assertEqual('08122233301', obj.mobile)

    def test_small_alpha_clinic(self):
        """Test that we interprete 'i' as 1 in clinic."""
        reg_data = {'text': 'i 08122233301 400 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg % 400)

        # Test that visit is saved
        self.assertEqual(1, models.Visit.objects.count())

    def test_big_alpha_clinic(self):
        """Test that we interprete 'I' as 1 in clinic."""
        reg_data = {'text': 'I 08122233301 400 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg % 400)

        # Test that visit is saved
        self.assertEqual(1, models.Visit.objects.count())

    def test_alpha_mobile(self):
        """Test that we interprete 'i' or 'I' as 1 in mobile."""
        reg_data = {'text': '1 08I2223330i 4000 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg % 4000)

        # Test that visit is saved
        self.assertEqual(1, models.Visit.objects.count())

        # Test that correct mobile is saved
        obj = models.Visit.objects.all()[0]
        self.assertEqual('08122233301', obj.mobile)

    def test_alpha_mixed(self):
        """Test that we interprete 'i', 'I' as 1; 'o', 'O' as 0 in serial."""
        reg_data = {'text': 'i 08I2223330i 4oI 5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg % 401)

        # Test that visit is saved
        self.assertEqual(1, models.Visit.objects.count())

        # Test that correct mobile is saved
        obj = models.Visit.objects.all()[0]
        self.assertEqual('08122233301', obj.mobile)

    def test_newline_as_whitespace(self):
        """Test that <enter> is treated like <space>."""
        reg_data = {'text': '1\n08122233301\n401\n5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg % 401)

        # Test that visit is saved
        self.assertEqual(1, models.Visit.objects.count())

        # Test the values are correctly saved
        obj = models.Visit.objects.all()[0]
        self.assertEqual(obj.patient.clinic, self.clinic)
        self.assertEqual('08122233301', obj.mobile)
        self.assertEqual(401, obj.patient.serial)

        # Test that correct mobile is saved
        obj = models.Visit.objects.all()[0]
        self.assertEqual('08122233301', obj.mobile)

    def test_multiple_whitespace(self):
        """Test that up to 3 whitespaces(mixed) are treated as one whitespace."""
        reg_data = {'text': '1\n  08122233301 \n 401\n5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg % 401)

        # Test that visit is saved
        self.assertEqual(1, models.Visit.objects.count())

        # Test the values are correctly saved
        obj = models.Visit.objects.all()[0]
        self.assertEqual(obj.patient.clinic, self.clinic)
        self.assertEqual('08122233301', obj.mobile)

    def test_asterisk_as_whitespace(self):
        """Test that '*' is treated as <space>."""
        reg_data = {'text': '1*08122233301*401*5', 'phone': '+2348022112211'}
        response = self.make_request(reg_data)
        self.assertEqual(response.content, self.success_msg % 401)

        # Test that visit is saved
        self.assertEqual(1, models.Visit.objects.count())

        # Test the values are correctly saved
        obj = models.Visit.objects.all()[0]
        self.assertEqual(obj.patient.clinic, self.clinic)
        self.assertEqual('08122233301', obj.mobile)

    def test_clinic_error_removed(self):
        """Test that when 3nd clinic error is sent, VisitRegistrationError is cleared."""
        reg_data = {'text': '21 08122233301*401*5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        self.assertEqual(1, models.VisitRegistrationError.objects.count())

        # 2nd time
        self.make_request(reg_data)
        self.assertEqual(2, models.VisitRegistrationError.objects.count())

        # 3rd time
        self.make_request(reg_data)
        self.assertEqual(0, models.VisitRegistrationError.objects.count())

    def test_serial_startswith_0(self):
        """Test that serials starting with '0' are valid."""
        reg_data = {'text': '1 08122233301 0401 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        self.assertEqual(1, models.Visit.objects.count())


class TestFeedbackView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.clinic = factories.Clinic.create(code=1)
        self.phone = '+12065551212'
        self.values = [
            {"category": "1", "value": "1", "label": "Clinic"},
            {"category": "All Responses", "value": "text", "label": "General Feedback"},
        ]

    def make_request(self, data):
        """Make test request with POST data."""
        request = self.factory.post('/clinics/feedback/', data=data)
        return clinics.FeedbackView.as_view()(request)

    def test_feedback_status(self):
        """Test that feedback view returns status_code 200."""
        feedback = {
            "phone": self.phone,
            "values": json.dumps(self.values)
        }
        response = self.make_request(feedback)
        self.assertEqual(200, response.status_code)

    def test_feedback_saved(self):
        """Test that feedback is saved."""
        feedback = {
            "phone": self.phone,
            "values": json.dumps(self.values)
        }
        self.make_request(feedback)
        self.assertEqual(1, models.GenericFeedback.objects.count())

        obj = models.GenericFeedback.objects.get(sender=self.phone)
        self.assertEqual('text', obj.message)
        self.assertEqual(self.clinic, obj.clinic)

    def test_feedback_noclinic_saved(self):
        """Test that feedback without clinic is saved with the clinic name
        in message field."""
        values = [
            {"category": "Other", "value": "none", "label": "Clinic"},
            {"category": "Other", "value": "none", "label": "Clinic"},
            {"category": "All Responses", "value": "none", "label": "Which Clinic"},
            {"category": "All Responses", "value": "no", "label": "General Feedback"},
        ]

        feedback = {
            "phone": self.phone,
            "values": json.dumps(values)
        }
        self.make_request(feedback)
        obj = models.GenericFeedback.objects.get(sender=self.phone)
        self.assertEqual('no (none)', obj.message)
        self.assertIsNone(obj.clinic)


class TestClinicReportView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.clinic = factories.Clinic.create(code=1)
        self.service = factories.Service.create(code=5)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)
        self.questions = []
        for l in ['Open Facility', 'Respectful Staff Treatment',
                  'Clean Hospital Materials', 'Charged Fairly',
                  'Wait Time']:
            self.questions.append(factories.SurveyQuestion.create(label=l, survey=self.survey))

    def make_request(self, data=None):
        """Make Test request with POST data."""
        if data is None:
            data = {}
        url = '/reports/facility/{}/'.format(self.clinic.slug)
        request = self.factory.get(url, data=data)
        return clinics.ClinicReport.as_view()(request, slug=self.clinic.slug)

    def test_clinic_report_page_loads(self):
        """Smoke test to make sure the page loads and returns some content."""
        response = self.make_request()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(bool(response.render()))

    def test_check_assumptions(self):
        """Test that if hard-coded assumptions are not met, exception is raised."""
        survey_models.SurveyQuestion.objects.filter(label='Open Facility').delete()
        self.assertRaises(Exception, self.make_request)

    def test_get_detailed_comments(self):
        """Test that generic feedback is combined with open-ended survey responses."""
        visit1 = factories.Visit.create(
            service=factories.Service.create(code=2),
            patient=factories.Patient.create(
                clinic=self.clinic,
                serial=221)
        )
        visit2 = factories.Visit.create(
            service=factories.Service.create(code=3),
            patient=factories.Patient.create(
                clinic=self.clinic,
                serial=111)
        )

        factories.SurveyQuestionResponse.create(
            question=factories.SurveyQuestion.create(
                label='General Feedback',
                survey=self.survey,
                question_type=survey_models.SurveyQuestion.OPEN_ENDED),
            response='Second',
            datetime=timezone.now()-timezone.timedelta(3),
            visit=visit1,
            clinic=self.clinic)
        factories.SurveyQuestionResponse.create(
            question=factories.SurveyQuestion.create(
                label='What question',
                survey=self.survey,
                question_type=survey_models.SurveyQuestion.OPEN_ENDED),
            response='First',
            datetime=timezone.now()-timezone.timedelta(5),
            visit=visit2,
            clinic=self.clinic)

        factories.GenericFeedback.create(
            clinic=self.clinic,
            message='Feedback message',
            message_date=timezone.now())

        report = clinics.ClinicReport(kwargs={'slug': self.clinic.slug})

        report.get_object()

        comments = report.get_detailed_comments()

        # Basic checks
        self.assertEqual(3, len(comments))

        # Check content of comments are sorted by question and datetime
        self.assertEqual('Second', comments[0]['response'])
        self.assertEqual('Feedback message', comments[1]['response'])
        self.assertEqual('First', comments[2]['response'])

    def test_hide_invalid_feedback(self):
        question = factories.SurveyQuestion(
            label='General', survey=self.survey,
            question_type=survey_models.SurveyQuestion.OPEN_ENDED)
        factories.SurveyQuestionResponse(
            question=question, response='No',
            visit=factories.Visit(patient__clinic=self.clinic))
        factories.SurveyQuestionResponse(
            question=question, response='Hello',
            visit=factories.Visit(patient__clinic=self.clinic))
        factories.SurveyQuestionResponse(
            question=question, response='Staff feedback that was hidden manually',
            visit=factories.Visit(patient__clinic=self.clinic),
            display_on_dashboard=False)
        factories.GenericFeedback(
            clinic=self.clinic, message_date=timezone.now(), message='No')
        factories.GenericFeedback(
            clinic=self.clinic, message_date=timezone.now(), message='Hello2')

        report = clinics.ClinicReport(kwargs={'slug': self.clinic.slug})
        report.get_object()
        comments = report.get_detailed_comments()
        self.assertEqual(2, len(comments))
        self.assertEqual(comments[0]['question'], 'General')
        self.assertEqual(comments[0]['response'], 'Hello')
        self.assertEqual(comments[1]['question'], 'General Feedback')
        self.assertEqual(comments[1]['response'], 'Hello2')


class TestAnalystDashboardView(TestCase):

    def setUp(self):
        now = datetime.datetime.now(pytz.utc)
        self.factory = RequestFactory()
        self.clinic = factories.Clinic.create(code=1)
        self.service = factories.Service.create(code=5)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)
        self.visit = factories.Visit.create(
            patient=self.patient, service=self.service, survey_sent=now)
        self.question = factories.SurveyQuestion.create(
            label="Wait Time", question_type="open-ended")
        self.surveyquestionresponse = factories.SurveyQuestionResponse.create(
            question=self.question, clinic=self.clinic, visit=self.visit)

    def make_request(self, data=None):
        """Make test request."""
        request = self.factory.get('/analyst_summary/')
        return clinics.AnalystSummary.as_view()(request)

    def test_clinic_report_page_loads(self):
        """Smoke test to make sure the page loads and returns some content."""
        response = self.make_request()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(bool(response.render()))

    def test_st_count(self):
        """ Tests how many Surveys have been 'triggered' """
        st_query = clinics.Visit.objects.filter(
            survey_sent__isnull=False, patient__clinic=self.clinic)
        self.assertEqual(st_query.count(), 1)

        now = datetime.datetime.now(pytz.utc)
        factories.Visit.create(
            service=factories.Service.create(code=2),
            patient=factories.Patient.create(
                clinic=self.clinic,
                serial=221),
            survey_sent=now
        )

        self.assertEqual(st_query.count(), 2)

    def test_ss_count(self):
        """ Tests how many Surveys have been 'started' using first question type (open-ended) """
        ss_query = survey_models.SurveyQuestionResponse.objects\
            .filter(question__question_type__iexact="open-ended")

        # We should have one from the setup
        self.assertEqual(ss_query.count(), 1)

        now = datetime.datetime.now(pytz.utc)

        visit1 = factories.Visit.create(
            service=factories.Service.create(code=2),
            patient=factories.Patient.create(
                clinic=self.clinic,
                serial=221),
            survey_sent=now
        )

        # Add another and see how we fare
        factories.SurveyQuestionResponse.create(
            question=self.question, clinic=self.clinic, visit=visit1)

        # Test the additional
        self.assertEqual(ss_query.count(), 2)

    def test_sc_count(self):
        """ Tests how many Surveys have been 'completed' using last question (Wait Time)"""

        sc_query = survey_models.SurveyQuestionResponse.objects\
            .filter(question__label="Wait Time").filter(clinic=self.clinic)

        # Test the setup materials
        self.assertEqual(sc_query.count(), 1)

        # Add a few
        now = datetime.datetime.now(pytz.utc)

        visit1 = factories.Visit.create(
            service=factories.Service.create(code=2),
            patient=factories.Patient.create(
                clinic=self.clinic,
                serial=223),
            survey_sent=now
        )

        factories.SurveyQuestionResponse.create(
            question=self.question, clinic=self.clinic, visit=visit1)

        # Test we have the right query
        self.assertEqual(sc_query.count(), 2)

