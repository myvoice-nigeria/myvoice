from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone
from django.contrib.gis.geos import GEOSGeometry

import json
import datetime
import pytz
import decimal

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

    def test_hour_to_hr(self):
        self.assertEqual('<1 hr', clinics.hour_to_hr('<1 hour'))

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
        """Test that a right entry after wrong entry clears the slate.

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

        self.assertEqual(1, models.VisitRegistrationError.objects.filter(
            sender='+2348022112211').count())

        # 2nd entry, Clinic is right
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)

        # Errors are cleared
        self.assertEqual(0, models.VisitRegistrationError.objects.filter(
            sender='+2348022112211').count())

        # 3rd entry, Clinic is wrong
        reg_data = {'text': '2 08122233301 4001 5', 'phone': '+2348022112211'}
        msg = self.error_msg % (4001, 'CLINIC')
        response = self.make_request(reg_data)
        self.assertEqual(response.content, msg)

        # Errors is back
        self.assertEqual(1, models.VisitRegistrationError.objects.filter(
            sender='+2348022112211').count())

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

    def test_save_sender(self):
        """Test that the sender information is saved."""
        reg_data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        self.make_request(reg_data)
        obj = models.Visit.objects.all()[0]
        self.assertEqual('08022112211', obj.sender)

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

    def test_long_feedback(self):
        self.values[1]['value'] = "a" * 260
        feedback = {
            'phone': self.phone,
            'values': json.dumps(self.values),
        }
        self.make_request(feedback)
        obj = models.GenericFeedback.objects.get(sender=self.phone)
        self.assertEqual("a" * 260, obj.message)


class TestReportMixin(TestCase):

    def setUp(self):
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)

        self.clinic = factories.Clinic.create(code=5)

        self.q1 = factories.SurveyQuestion.create(
            label='One',
            survey=self.survey,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            start_date=timezone.make_aware(timezone.datetime(2014, 8, 30), timezone.utc),
            categories='Yes\nNo',
            report_order=10)
        self.q2 = factories.SurveyQuestion.create(
            label='two',
            survey=self.survey,
            question_type=survey_models.SurveyQuestion.OPEN_ENDED,
            report_order=20)
        self.q3 = factories.SurveyQuestion.create(
            label='Three',
            survey=self.survey,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            categories='Yes\nNo',
            report_order=30)
        self.q4 = factories.SurveyQuestion.create(
            label='Four',
            survey=self.survey,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            end_date=timezone.make_aware(timezone.datetime(2014, 8, 10), timezone.utc),
            categories='Yes\nNo',
            report_order=40)
        self.q5 = factories.SurveyQuestion.create(
            label='Five',
            survey=self.survey,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            start_date=timezone.now(),
            categories='Yes\nNo',
            report_order=50)

        self.p1 = factories.Patient.create(clinic=self.clinic, serial=111)
        self.p2 = factories.Patient.create(clinic=self.clinic, serial=222)
        self.p3 = factories.Patient.create(clinic=self.clinic, serial=333)

        self.s1 = factories.Service.create(code=1)
        self.s2 = factories.Service.create(code=2)
        self.s3 = factories.Service.create(code=3)

        sent = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        self.v1 = factories.Visit.create(service=self.s1, patient=self.p1, survey_sent=sent)
        self.v2 = factories.Visit.create(service=self.s2, patient=self.p2, survey_sent=sent)
        self.v3 = factories.Visit.create(service=self.s3, patient=self.p3, survey_sent=sent)
        self.v4 = factories.Visit.create(service=self.s1, patient=self.p1, survey_sent=sent)

        self.r1 = factories.SurveyQuestionResponse.create(
            question=self.q1, visit=self.v1, clinic=self.clinic, response='Yes')
        self.r2 = factories.SurveyQuestionResponse.create(
            question=self.q2, visit=self.v2, clinic=self.clinic)
        self.r3 = factories.SurveyQuestionResponse.create(
            question=self.q3, visit=self.v3, clinic=self.clinic, response='No')
        self.r4 = factories.SurveyQuestionResponse.create(
            question=self.q2, visit=self.v4, clinic=self.clinic)

    def test_get_start_end_dates(self):
        """Test that we can break down a start and end dates
        to week boundaries."""
        d1 = timezone.make_aware(timezone.datetime(2014, 9, 1), timezone.utc)
        d2 = timezone.make_aware(timezone.datetime(2014, 9, 15), timezone.utc)

        mixin = clinics.ReportMixin()
        week_ranges = list(mixin.get_week_ranges(d1, d2))

        self.assertEqual(3, len(week_ranges))
        self.assertEqual(
            (
                timezone.make_aware(
                    timezone.datetime(2014, 9, 1, 0, 0, 0), timezone.utc),
                timezone.make_aware(
                    timezone.datetime(2014, 9, 7, 23, 59, 59, 999999), timezone.utc)),
            week_ranges[0])
        self.assertEqual(
            (
                timezone.make_aware(
                    timezone.datetime(2014, 9, 8, 0, 0, 0), timezone.utc),
                timezone.make_aware(
                    timezone.datetime(2014, 9, 14, 23, 59, 59, 999999), timezone.utc)),
            week_ranges[1])
        self.assertEqual(
            (
                timezone.make_aware(
                    timezone.datetime(2014, 9, 15, 0, 0, 0), timezone.utc),
                timezone.make_aware(
                    timezone.datetime(2014, 9, 21, 23, 59, 59, 999999), timezone.utc)),
            week_ranges[2])

    def test_get_week_ranges_future(self):
        """Test that if week_end is in the future,
        we make week_end today and week_start 6 days ago."""
        d1 = timezone.make_aware(timezone.datetime(2014, 9, 1), timezone.utc)
        d2 = timezone.make_aware(timezone.datetime(2014, 9, 15), timezone.utc)
        curr_dt = timezone.make_aware(timezone.datetime(2014, 9, 19), timezone.utc)

        mixin = clinics.ReportMixin()
        week_ranges = list(mixin.get_week_ranges(d1, d2, curr_dt))

        self.assertEqual(3, len(week_ranges))
        self.assertEqual(
            (
                timezone.make_aware(
                    timezone.datetime(2014, 9, 13, 0, 0, 0), timezone.utc),
                timezone.make_aware(
                    timezone.datetime(2014, 9, 19, 23, 59, 59, 999999), timezone.utc)),
            week_ranges[2])

    def test_get_survey_questions(self):
        """Test that get_survey_questions returns correct questions.

        Start and end dates are passed into the method.
        Returns SurveyQuestions that are:
        1. Valid for at least part of the range
        2. are multiple-choice questions.

        P.S.
        SurveyQuestions are ordered by report_order.
        If no dates are passed, current week is used as default.
        """
        from datetime import date
        one = factories.SurveyQuestion.create(
            label='another one',
            survey=self.survey,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=70,
            start_date=date(2014, 8, 15))
        two = factories.SurveyQuestion.create(
            label='another two',
            survey=self.survey,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=80,
            start_date=date(2014, 8, 21))
        mixin = clinics.ReportMixin()
        start_date = timezone.make_aware(timezone.datetime(2014, 8, 14), timezone.utc)
        end_date = timezone.make_aware(timezone.datetime(2014, 8, 21), timezone.utc)
        questions = mixin.get_survey_questions(start_date, end_date)

        self.assertEqual(3, len(questions))
        self.assertEqual(self.q3, questions[0])
        self.assertEqual(one, questions[1])
        self.assertEqual(two, questions[2])

    def test_get_survey_questions_default_week(self):
        """Test that if no start_date is passed, the current week is used."""
        mixin = clinics.ReportMixin()
        questions = mixin.get_survey_questions()

        self.assertEqual(3, len(questions))
        self.assertTrue(self.q1 in questions)
        self.assertTrue(self.q3 in questions)
        self.assertTrue(self.q5 in questions)

    def test_get_survey_questions_order(self):
        """Test that responses are ordered by report_order."""
        mixin = clinics.ReportMixin()
        start_date = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        end_date = timezone.make_aware(timezone.datetime(2014, 8, 31), timezone.utc)
        questions = mixin.get_survey_questions(start_date, end_date)

        self.assertEqual(2, len(questions))
        self.assertEqual(self.q1, questions[0])
        self.assertEqual(self.q3, questions[1])

    def test_get_feedback_participation(self):
        """Test that get_feedback_participation returns % of surveys responded
        to and total visit count."""
        mixin = clinics.ReportMixin()
        sent = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        v5 = factories.Visit.create(service=self.s1, patient=self.p2, survey_sent=sent)
        visits = models.Visit.objects.filter(
            pk__in=[self.v1.pk, self.v2.pk, self.v3.pk, v5.pk])
        percent, total_started = mixin.get_feedback_participation(visits)

        self.assertEqual(75, percent)
        self.assertEqual(3, total_started)

    def test_get_feedback_statistics(self):
        """Test get_feedback_statistics.

        Takes a list of clinics
        Returns 3 lists of surveys sent, started and completed
        in order of clinics passed in."""
        cl1 = factories.Clinic.create(code=1, lga='one')
        cl2 = factories.Clinic.create(code=2, lga='one')

        p1 = factories.Patient.create(clinic=cl1, serial=444)
        p2 = factories.Patient.create(clinic=cl2, serial=555)

        sent = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        factories.Visit.create(
            service=self.s1,
            patient=p1,
            survey_sent=sent,
            survey_started=True,
            survey_completed=True,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 1), timezone.utc))
        factories.Visit.create(
            service=self.s2,
            patient=p1,
            survey_sent=sent,
            survey_started=True,
            survey_completed=False,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 5), timezone.utc))
        factories.Visit.create(
            service=self.s3,
            patient=p1,
            survey_sent=sent,
            survey_started=True,
            survey_completed=True,
            visit_time=timezone.make_aware(timezone.datetime(2014, 11, 1), timezone.utc))
        factories.Visit.create(
            service=self.s2,
            patient=p2,
            survey_sent=sent,
            survey_started=True,
            survey_completed=True,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 10), timezone.utc))
        factories.Visit.create(
            service=self.s2,
            patient=p2,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 10), timezone.utc))

        mixin = clinics.ReportMixin()
        start = timezone.make_aware(timezone.datetime(2014, 12, 1), timezone.utc)
        end = timezone.make_aware(timezone.datetime(2014, 12, 31), timezone.utc)
        stats = mixin.get_feedback_statistics([cl1, cl2], start, end)

        self.assertEqual(3, len(stats))
        self.assertEqual([100, 50], stats['sent'])
        self.assertEqual([100, 50], stats['started'])
        self.assertEqual([50, 50], stats['completed'])

    def test_get_feedback_statistics_no_dates(self):
        """Test get_feedback_statistics with no start/end dates passed in takes all the visits
        """

        cl1 = factories.Clinic.create(code=1, lga='one')
        cl2 = factories.Clinic.create(code=2, lga='one')

        p1 = factories.Patient.create(clinic=cl1, serial=444)
        p2 = factories.Patient.create(clinic=cl2, serial=555)

        sent = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        factories.Visit.create(
            service=self.s1,
            patient=p1,
            survey_sent=sent,
            survey_started=True,
            survey_completed=True,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 1), timezone.utc))
        factories.Visit.create(
            service=self.s2,
            patient=p1,
            survey_sent=sent,
            survey_started=True,
            survey_completed=False,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 5), timezone.utc))
        factories.Visit.create(
            service=self.s3,
            patient=p1,
            survey_sent=sent,
            survey_started=True,
            survey_completed=True,
            visit_time=timezone.make_aware(timezone.datetime(2014, 11, 1), timezone.utc))
        factories.Visit.create(
            service=self.s2,
            patient=p2,
            survey_sent=sent,
            survey_started=True,
            survey_completed=True,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 10), timezone.utc))
        factories.Visit.create(
            service=self.s2,
            patient=p2,
            visit_time=timezone.make_aware(timezone.datetime(2014, 12, 10), timezone.utc))

        mixin = clinics.ReportMixin()
        stats = mixin.get_feedback_statistics([cl1, cl2])

        self.assertEqual(3, len(stats))
        self.assertEqual([100, 50], stats['sent'])
        self.assertEqual([100, 50], stats['started'])
        self.assertEqual([67, 50], stats['completed'])

    def test_feedback_response_statistics(self):
        """Test get_response_statistics.

        Takes list of clinics, survey questions, responses
        Returns list of:
          (Count of positive responses, %age of positive responses)
        """
        clinic = factories.Clinic.create(code=6)

        sent = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        p1 = factories.Patient.create(clinic=clinic, serial=111)
        v1 = factories.Visit.create(service=self.s1, patient=p1, survey_sent=sent)
        v2 = factories.Visit.create(service=self.s2, patient=p1, survey_sent=sent)
        v3 = factories.Visit.create(service=self.s3, patient=p1, survey_sent=sent)

        factories.SurveyQuestionResponse.create(
            question=self.q4, visit=v1, clinic=clinic, response='Yes')
        factories.SurveyQuestionResponse.create(
            question=self.q4, visit=v3, clinic=clinic, response='No')
        factories.SurveyQuestionResponse.create(
            question=self.q4, visit=v2, clinic=clinic, response='Yes')

        mixin = clinics.ReportMixin()
        questions = [self.q1, self.q4]
        stats = mixin.get_response_statistics([self.clinic, clinic], questions)

        self.assertEqual(1, stats[0][0])
        self.assertEqual('100.0%', stats[0][1])
        self.assertEqual(2, stats[1][0])
        self.assertEqual('67.0%', stats[1][1])

    def test_feedback_response_statistics_daterange(self):
        """Test get_response_statistics respects date ranges.

        Takes list of clinics, survey questions, responses, start and end dates
        Returns list of:
          (Count of positive responses, %age of positive responses)
        """
        clinic = factories.Clinic.create(code=6)

        sent = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        time1 = timezone.make_aware(timezone.datetime(2014, 8, 5), timezone.utc)
        time2 = timezone.make_aware(timezone.datetime(2014, 8, 15), timezone.utc)
        time3 = timezone.make_aware(timezone.datetime(2014, 8, 25), timezone.utc)
        p1 = factories.Patient.create(clinic=clinic, serial=111)
        v1 = factories.Visit.create(
            service=self.s1, patient=p1, survey_sent=sent, visit_time=time1)
        v2 = factories.Visit.create(
            service=self.s2, patient=p1, survey_sent=sent, visit_time=time2)
        v3 = factories.Visit.create(
            service=self.s3, patient=p1, survey_sent=sent, visit_time=time3)

        factories.SurveyQuestionResponse.create(
            question=self.q4, visit=v1, clinic=clinic, response='Yes')
        factories.SurveyQuestionResponse.create(
            question=self.q4, visit=v2, clinic=clinic, response='No')
        factories.SurveyQuestionResponse.create(
            question=self.q4, visit=v3, clinic=clinic, response='Yes')

        mixin = clinics.ReportMixin()
        questions = [self.q1, self.q4]
        stats = mixin.get_response_statistics([clinic], questions, time1, time2)

        self.assertEqual(0, stats[0][0])
        self.assertIsNone(stats[0][1])
        self.assertEqual(1, stats[1][0])
        self.assertEqual('50.0%', stats[1][1])


class TestClinicReportView(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.clinic = factories.Clinic.create(code=1)
        self.service = factories.Service.create(code=5)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)
        self.questions = []

        self.open_facility = factories.SurveyQuestion.create(
            label='Open Facility',
            survey=self.survey,
            categories='Open\nClosed',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE)
        self.questions.append(self.open_facility)
        self.respect = factories.SurveyQuestion.create(
            label='Respectful Staff Treatment',
            survey=self.survey, categories='Yes\nNo', primary_answer='Yes',
            for_satisfaction=True,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE)
        self.questions.append(self.respect)
        self.questions.append(factories.SurveyQuestion.create(
            label='Clean Hospital Materials',
            survey=self.survey))
        self.questions.append(factories.SurveyQuestion.create(
            label='Charged Fairly',
            survey=self.survey,
            categories='Fairly charged\nOvercharged', primary_answer='Fairly charged',
            for_satisfaction=True,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE))
        self.questions.append(factories.SurveyQuestion.create(
            label='Wait Time',
            survey=self.survey, categories='<1 hour\n1-2 hours\n2-4 hours\n>4 hours',
            for_satisfaction=True,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE))

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

    def test_get_feedback_by_week(self):
        """Test that get_feedback_by_week works."""
        clinic = factories.Clinic.create(code=7)

        v1 = factories.Visit.create(
            service=factories.Service.create(code=2),
            visit_time=timezone.make_aware(timezone.datetime(2014, 7, 25), timezone.utc),
            survey_sent=timezone.make_aware(timezone.datetime(2014, 7, 25), timezone.utc),
            patient=factories.Patient.create(clinic=clinic, serial=221))
        v2 = factories.Visit.create(
            service=factories.Service.create(code=3),
            visit_time=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            survey_sent=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            patient=factories.Patient.create(clinic=clinic, serial=111))
        v3 = factories.Visit.create(
            service=factories.Service.create(code=4),
            visit_time=timezone.make_aware(timezone.datetime(2014, 7, 30), timezone.utc),
            survey_sent=timezone.make_aware(timezone.datetime(2014, 7, 30), timezone.utc),
            patient=factories.Patient.create(clinic=clinic, serial=121))

        factories.SurveyQuestionResponse.create(
            question=self.open_facility,
            response='Open',
            datetime=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            visit=v1,
            clinic=clinic)
        factories.SurveyQuestionResponse.create(
            question=self.open_facility,
            response='Closed',
            datetime=timezone.make_aware(timezone.datetime(2014, 7, 27), timezone.utc),
            visit=v2,
            clinic=clinic)
        factories.SurveyQuestionResponse.create(
            question=self.open_facility,
            response='Open',
            datetime=timezone.make_aware(timezone.datetime(2014, 7, 30), timezone.utc),
            visit=v3,
            clinic=clinic)
        factories.SurveyQuestionResponse.create(
            question=self.respect,
            response='Yes',
            datetime=timezone.make_aware(timezone.datetime(2014, 7, 30), timezone.utc),
            visit=v3,
            clinic=clinic)

        report = clinics.ClinicReport(kwargs={'slug': clinic.slug})

        report.get_object()
        feedback = report.get_feedback_by_week()

        # More checks
        self.assertEqual(2, feedback[0]['survey_num'])
        self.assertEqual(None, feedback[0]['patient_satisfaction'])
        self.assertEqual(1, feedback[1]['survey_num'])
        self.assertEqual(100, feedback[1]['patient_satisfaction'])

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
        factories.GenericFeedback(
            clinic=self.clinic,
            message_date=timezone.now(),
            message='Hello2',
            display_on_dashboard=False)

        report = clinics.ClinicReport(kwargs={'slug': self.clinic.slug})
        report.get_object()
        comments = report.get_detailed_comments()
        self.assertEqual(2, len(comments))
        self.assertEqual(comments[0]['question'], 'General')
        self.assertEqual(comments[0]['response'], 'Hello')
        self.assertEqual(comments[1]['question'], 'General Feedback')
        self.assertEqual(comments[1]['response'], 'Hello2')


class TestClinicReportFilterByWeek(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)
        self.clinic = factories.Clinic.create(code=1)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)

        self.facility = factories.SurveyQuestion.create(
            label='Open Facility',
            survey=self.survey,
            categories='Open\nClosed',
            primary_answer='Open',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=10)

        self.respect = factories.SurveyQuestion.create(
            label='Respectful Staff Treatment',
            survey=self.survey,
            categories='Yes\nNo',
            primary_answer='Yes',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=20)

        # Unfortunately, 'Wait Time' is compulsory so far...
        self.wait = factories.SurveyQuestion.create(
            label='Wait Time',
            survey=self.survey,
            categories='<1 hour\n1-2 hours\n2-4 hours\n>4 hours',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=30)

    def make_request(self, data=None):
        if data is None:
            data = {}
        url = '/report_filter_feedback_by_week/'
        request = self.factory.get(url, data=data)
        return clinics.ClinicReportFilterByWeek.as_view()(request)

    def test_request_load(self):
        data = {
            'start_date': 'August 01, 2014',
            'end_date': 'August 08, 2014',
            'clinic_id': self.clinic.id}
        response = self.make_request(data)
        self.assertEqual(response.status_code, 200)

    def test_get_feedback_data(self):
        service1 = factories.Service.create(code=1)
        service2 = factories.Service.create(code=2)

        v1 = factories.Visit.create(
            service=service1,
            visit_time=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=221)
        )
        v2 = factories.Visit.create(
            service=service2,
            visit_time=timezone.make_aware(timezone.datetime(2014, 8, 6), timezone.utc),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=111)
        )

        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            visit=v1,
            clinic=self.clinic, response='Yes')

        factories.SurveyQuestionResponse.create(
            question=self.facility,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 8), timezone.utc),
            visit=v1,
            clinic=self.clinic, response='Yes')

        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 6), timezone.utc),
            visit=v2,
            clinic=self.clinic, response='Yes')

        self.wait_response = factories.SurveyQuestionResponse.create(
            question=self.wait,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 3), timezone.utc),
            visit=v2,
            clinic=self.clinic, response='<1 hour')

        start_date = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        end_date = timezone.make_aware(timezone.datetime(2014, 8, 7), timezone.utc)
        report = clinics.ClinicReportFilterByWeek()
        data = report.get_feedback_data(start_date, end_date, self.clinic)
        data_dict = dict([(i[0], i[1]) for i in data['fos']])

        self.assertEqual(2, len(data['fos']))
        self.assertEqual(
            [
                (u'Open Facility', '0.0%', 0),
                (u'Respectful Staff Treatment', None, 0),
                (u'Wait Time', None, 0)
                ], data_dict[service1.name])
        self.assertEqual(
            [
                (u'Open Facility', None, 0),
                (u'Respectful Staff Treatment', '100.0%', 1),
                (u'Wait Time', '<1 hr', 1)
                ], data_dict[service2.name])


class TestAnalystDashboardView(TestCase):

    def setUp(self):
        now = timezone.now()
        self.factory = RequestFactory()
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)
        self.clinic = factories.Clinic.create(code=1)
        self.service = factories.Service.create(code=5)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)
        self.visit = factories.Visit.create(
            patient=self.patient, service=self.service, survey_sent=now, visit_time=timezone.now())
        self.question = factories.SurveyQuestion.create(
            survey=self.survey, label="Wait Time", question_type="open-ended")
        self.surveyquestionresponse = factories.SurveyQuestionResponse.create(
            question=self.question, clinic=self.clinic, visit=self.visit)

        self.clinic1 = factories.Clinic.create(code=2)
        self.clinic2 = factories.Clinic.create(code=3)
        self.clinics = clinics.Clinic.objects.filter(code__in=[2, 3])

        self.patient1 = factories.Patient.create(serial='2111', clinic=self.clinic1)
        self.patient2 = factories.Patient.create(serial='2222', clinic=self.clinic2)
        visit_time = timezone.make_aware(timezone.datetime(2014, 7, 1), timezone.utc)

        factories.Visit.create(
            patient=self.patient1,
            survey_sent=now,
            service=self.service,
            visit_time=visit_time)

        factories.Visit.create(
            patient=self.patient1, survey_sent=now, service=self.service)
        factories.Visit.create(
            patient=self.patient2, survey_sent=now, service=self.service)
        factories.Visit.create(
            patient=self.patient1, survey_sent=None, service=self.service)

        q1 = factories.SurveyQuestion.create(
            survey=self.survey, label='Open Facility', question_type='multiple-choice')

        factories.SurveyQuestionResponse(
            question=q1,
            clinic=self.clinic1,
            visit=factories.Visit.create(
                patient=self.patient1, service=self.service)
        )
        factories.SurveyQuestionResponse(
            question=q1,
            clinic=self.clinic1,
            visit=factories.Visit.create(
                patient=self.patient1, service=self.service)
        )
        factories.SurveyQuestionResponse(
            question=q1,
            clinic=self.clinic2,
            visit=factories.Visit.create(
                patient=self.patient2, service=self.service)
        )

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
            survey_sent=now,
            visit_time=timezone.now()
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

    def test_completion_table(self):
        """Test that the get_completion_table method returns a list of dicts of calculations."""
        now = timezone.now()

        dt1 = timezone.make_aware(timezone.datetime(2014, 7, 20), timezone.utc)
        dt2 = timezone.make_aware(timezone.datetime(2014, 7, 25), timezone.utc)
        dt3 = timezone.make_aware(timezone.datetime(2014, 7, 27), timezone.utc)

        factories.Visit.create(
            patient=self.patient1, survey_sent=now, visit_time=dt1, service=self.service)
        factories.Visit.create(
            patient=self.patient1, survey_sent=now, visit_time=dt2, service=self.service)
        factories.Visit.create(
            patient=self.patient2, survey_sent=now, visit_time=dt2, service=self.service)
        factories.Visit.create(
            patient=self.patient1, survey_sent=now, visit_time=dt3, service=self.service)

        start = timezone.datetime(2014, 7, 20).strftime('%Y-%m-%d')
        end = timezone.datetime(2014, 7, 30).strftime('%Y-%m-%d')

        table = clinics.AnalystSummary().get_completion_table(
            start_date=start, end_date=end, service=self.service)
        # 3 clinics + total
        self.assertEqual(4, len(table))

    def _test_get_survey_started_counts(self):
        """Test that get_started_survey_counts returns
        count of all surveys started by clinic."""
        qset = survey_models.SurveyQuestionResponse.objects.filter()
        counts = clinics.AnalystSummary.get_survey_counts(qset, self.clinics)
        self.assertEqual(2, len(counts))

        self.assertEqual(2, counts[self.clinic1])
        self.assertEqual(1, counts[self.clinic2])


class TestFeedbackFilterView(TestCase):
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

    def test_request(self):
        url = '/clinics/feedback_filter/?clinic=&service=ANC&start_date&end_date='
        request = self.factory.get(url)
        response = clinics.FeedbackFilter.as_view()(request)
        self.assertEqual(200, response.status_code)


class TestRegionReportView(TestCase):

    def setUp(self):
        geom = GEOSGeometry('MULTIPOLYGON((( 1 1, 1 2, 2 2, 1 1)))')
        self.factory = RequestFactory()
        self.region = factories.Region.create(pk=599, name='Wamba', type='lga', boundary=geom)
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)

        self.open = factories.SurveyQuestion.create(
            label='Open Facility',
            survey=self.survey,
            categories="Open\nClosed",
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=10)
        self.respect = factories.SurveyQuestion.create(
            label='Respectful Staff Treatment',
            survey=self.survey, categories='Yes\nNo',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            for_satisfaction=True,
            report_order=20)
        self.clean = factories.SurveyQuestion.create(
            label='Clean Hospital Materials',
            survey=self.survey,
            categories="Clean\nNot Clean",
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=30)
        self.fair = factories.SurveyQuestion.create(
            label='Charged Fairly',
            survey=self.survey,
            categories='Yes\nNo',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            for_satisfaction=True,
            report_order=40)
        self.wait = factories.SurveyQuestion.create(
            label='Wait Time',
            survey=self.survey,
            categories='<1 hour\n1-2 hours\n2-3 hours\n4+ hours',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            last_negative=True,
            for_satisfaction=True,
            report_order=50)

        self.clinic = factories.Clinic.create(code=1, lga='Wamba', name='TEST1')

        self.service = factories.Service.create(code=2)

        self.v1 = factories.Visit.create(
            service=self.service,
            visit_time=timezone.now(),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=221)
        )
        self.v2 = factories.Visit.create(
            service=self.service,
            visit_time=timezone.now(),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=111)
        )

        factories.SurveyQuestionResponse.create(
            question=self.open,
            datetime=timezone.now(),
            visit=self.v1,
            clinic=self.clinic, response='Open')

        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.now(),
            visit=self.v2,
            clinic=self.clinic, response='No')

        self.wait_response = factories.SurveyQuestionResponse.create(
            question=self.wait,
            datetime=timezone.now(),
            visit=self.v2,
            clinic=self.clinic, response='<1 hour')

    def make_request(self, data=None):
        """Make Test request with POST data."""
        if data is None:
            data = {}
        url = '/reports/region/599/'
        request = self.factory.get(url, data=data)
        return clinics.RegionReport.as_view()(request, pk=599)

    def test_region_report_page_loads(self):
        """Smoke test to make sure page loads and returns some context."""
        response = self.make_request()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(bool(response.render))

    def test_default_responses(self):
        """Test that without date in request params, all responses used."""
        # Test that all responses are taken
        dt = timezone.now().replace(year=2014, month=7, day=14, second=0, microsecond=0)
        v2 = factories.Visit.create(
            service=factories.Service.create(code=3),
            visit_time=dt + timezone.timedelta(2),
            survey_sent=dt + timezone.timedelta(2),
            patient=factories.Patient.create(clinic=self.clinic, serial=115)
        )
        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.now(),
            visit=v2,
            clinic=self.clinic, response='No')

        url = '/reports/region/599/'
        request = self.factory.get(url)
        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.request = request
        report.get(request)

        self.assertEqual(4, report.responses.count())

    def test_bad_date_from_request_params(self):
        """Test that if date values from request params are wrong, all responses taken."""
        dt = timezone.now().replace(year=2014, month=7, day=14, second=0, microsecond=0)
        v2 = factories.Visit.create(
            service=factories.Service.create(code=3),
            visit_time=dt + timezone.timedelta(2),
            survey_sent=dt + timezone.timedelta(2),
            patient=factories.Patient.create(clinic=self.clinic, serial=115)
        )
        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.now(),
            visit=v2,
            clinic=self.clinic, response='No')

        url = '/reports/region/599/?day=x&month=7&year=2014'
        request = self.factory.get(url)
        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.request = request
        report.get(request)
        self.assertIsNone(report.curr_date)

        self.assertEqual(4, report.responses.count())

    def test_feedback_participation(self):
        # FIXME: Should this not be in the ReportMixin test?
        factories.Visit.create(
            service=self.service,
            visit_time=timezone.now(),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=311)
        )
        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()
        visits = models.Visit.objects.filter(
            patient__clinic=self.clinic, survey_sent__isnull=False)
        percent, total = report.get_feedback_participation(visits)
        self.assertEqual(67, percent)
        self.assertEqual(2, total)

    def test_get_satisfaction_counts(self):
        """Test number of visits that patient was not unsatisfied."""
        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        p1 = factories.Patient.create(serial=1111, clinic=self.clinic)
        p2 = factories.Patient.create(serial=2222, clinic=self.clinic)

        service = factories.Service.create(code=3)

        v1 = factories.Visit.create(patient=p1, service=service)
        v2 = factories.Visit.create(patient=p2, service=service)
        v3 = factories.Visit.create(patient=p1, service=service)
        v4 = factories.Visit.create(patient=p2, service=service)

        factories.SurveyQuestionResponse.create(
            question=self.respect, response='Yes', visit=v1)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='<1 hour', visit=v1)

        factories.SurveyQuestionResponse.create(
            question=self.respect, response='No', visit=v2)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='1-2 hours', visit=v2)

        factories.SurveyQuestionResponse.create(
            question=self.respect, response='Yes', visit=v3)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='<1 hour', visit=v3)

        factories.SurveyQuestionResponse.create(
            question=self.fair, response='Yes', visit=v4)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='<1 hour', visit=v4)

        report.get_object()

        responses = survey_models.SurveyQuestionResponse.objects.filter(clinic=self.clinic)
        satisfaction, total = report.get_satisfaction_counts(responses)
        self.assertEqual(60, satisfaction)
        self.assertEqual(3, total)

    def test_get_satisfaction_counts_waittime(self):
        """Test number of visits that patient was not unsatisfied because of Wait Time."""
        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        p1 = factories.Patient.create(serial=1111, clinic=self.clinic)
        p2 = factories.Patient.create(serial=2222, clinic=self.clinic)

        service = factories.Service.create(code=3)

        v1 = factories.Visit.create(patient=p1, service=service)
        v2 = factories.Visit.create(patient=p2, service=service)
        v3 = factories.Visit.create(patient=p1, service=service)
        v4 = factories.Visit.create(patient=p2, service=service)

        factories.SurveyQuestionResponse.create(
            question=self.respect, response='Yes', visit=v1)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='<1 hour', visit=v1)

        factories.SurveyQuestionResponse.create(
            question=self.respect, response='Yes', visit=v2)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='1-2 hours', visit=v2)

        factories.SurveyQuestionResponse.create(
            question=self.respect, response='Yes', visit=v3)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='<1 hour', visit=v3)

        factories.SurveyQuestionResponse.create(
            question=self.fair, response='Yes', visit=v4)
        factories.SurveyQuestionResponse.create(
            question=self.wait, response='4+ hours', visit=v4)
        report.get_object()

        responses = survey_models.SurveyQuestionResponse.objects.filter(clinic=self.clinic)
        satisfaction, total = report.get_satisfaction_counts(responses)
        self.assertEqual(60, satisfaction)
        self.assertEqual(3, total)

    def test_get_satisfaction_counts_no_responses(self):
        """Test get satisfaction counts with no responses."""
        clinic = factories.Clinic.create(code=3, lga='Wamba1', name='TEST2')

        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()

        responses = survey_models.SurveyQuestionResponse.objects.filter(clinic=clinic)
        satisfaction, total = report.get_satisfaction_counts(responses)
        self.assertEqual(None, satisfaction)
        self.assertEqual(0, total)

    def test_get_clinic_indices(self):
        """Test that we can get percentage and total count of
        responses per question."""
        factories.SurveyQuestionResponse.create(
            question=self.clean,
            datetime=timezone.now(),
            visit=self.v1,
            clinic=self.clinic, response='Clean')
        factories.SurveyQuestionResponse.create(
            question=self.clean,
            datetime=timezone.now(),
            visit=self.v2,
            clinic=self.clinic, response='Not Clean')

        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()
        responses = survey_models.SurveyQuestionResponse.objects.filter(clinic=self.clinic)
        target_questions = survey_models.SurveyQuestion.objects.filter(
            pk__in=[self.respect.id, self.clean.id, self.fair.id, self.open.id])
        indices = [i for i in report.get_indices(target_questions, responses)]
        self.assertEqual(4, len(indices))

        self.assertEqual(('Open Facility', '100.0%', 1), indices[0])
        self.assertEqual(('Respectful Staff Treatment', '0.0%', 0), indices[1])
        self.assertEqual(('Clean Hospital Materials', '50.0%', 1), indices[2])
        self.assertEqual(('Charged Fairly', None, 0), indices[3])

    def test_get_wait_time_mode(self):
        """Get the most frequent wait time."""
        v3 = factories.Visit.create(
            service=self.service,
            visit_time=timezone.now(),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=117)
        )
        factories.SurveyQuestionResponse.create(
            question=self.wait,
            datetime=timezone.now(),
            visit=self.v1,
            clinic=self.clinic, response='<1 hour')
        factories.SurveyQuestionResponse.create(
            question=self.wait,
            datetime=timezone.now(),
            visit=v3,
            clinic=self.clinic, response='1-2 hours')
        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()
        responses = survey_models.SurveyQuestionResponse.objects.filter(clinic=self.clinic)
        mode, mode_len = report.get_wait_mode(responses)

        self.assertEqual('<1 hour', mode)
        self.assertEqual(2, mode_len)

    def test_get_clinic_score(self):
        """Test that we can get quality and quantity scores."""
        factories.ClinicScore.create(
            clinic=self.clinic,
            quality=89.35,
            quantity=5000,
            start_date=timezone.datetime(2014, 7, 1),
            end_date=timezone.datetime(2014, 9, 30))
        factories.ClinicScore.create(
            clinic=self.clinic,
            quality=70.50,
            quantity=1200,
            start_date=timezone.datetime(2014, 4, 1),
            end_date=timezone.datetime(2014, 6, 30))

        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()

        d1 = timezone.datetime(2014, 5, 1)
        d2 = timezone.datetime(2014, 8, 1)

        score1 = report.get_clinic_score(self.clinic, d2)
        self.assertEqual(score1.quality, decimal.Decimal('89.35'))
        self.assertEqual(score1.quantity, 5000)

        score2 = report.get_clinic_score(self.clinic, d1)
        self.assertEqual(score2.quality, decimal.Decimal('70.50'))
        self.assertEqual(score2.quantity, 1200)

    def test_get_clinic_score_nodate(self):
        """Test that current date is used as default ref_date."""
        factories.ClinicScore.create(
            clinic=self.clinic,
            quality=89.35,
            quantity=5000,
            start_date=timezone.datetime(2014, 7, 1),
            end_date=timezone.now().date())

        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()

        score = report.get_clinic_score(self.clinic)
        self.assertEqual(score.quality, decimal.Decimal('89.35'))
        self.assertEqual(score.quantity, 5000)

    def test_get_clinic_score_overlap(self):
        """Test that when we have overlapping dates, return None as score."""
        factories.ClinicScore.create(
            clinic=self.clinic,
            quality=89.35,
            quantity=5000,
            start_date=timezone.datetime(2014, 7, 1),
            end_date=timezone.datetime(2014, 9, 30))
        factories.ClinicScore.create(
            clinic=self.clinic,
            quality=70.50,
            quantity=1200,
            start_date=timezone.datetime(2014, 4, 1),
            end_date=timezone.datetime(2014, 8, 30))

        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()

        dt = timezone.datetime(2014, 8, 20)

        score1 = report.get_clinic_score(self.clinic, dt)
        self.assertIsNone(score1)

    def test_get_clinic_score_none(self):
        """Test that when we have no scores for date, return None as score."""
        factories.ClinicScore.create(
            clinic=self.clinic,
            quality=89.35,
            quantity=5000,
            start_date=timezone.datetime(2014, 7, 1),
            end_date=timezone.datetime(2014, 9, 30))
        factories.ClinicScore.create(
            clinic=self.clinic,
            quality=70.50,
            quantity=1200,
            start_date=timezone.datetime(2014, 4, 1),
            end_date=timezone.datetime(2014, 8, 30))

        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()

        dt = timezone.datetime(2014, 1, 20)

        score1 = report.get_clinic_score(self.clinic, dt)
        self.assertIsNone(score1)

    def test_get_feedback_by_clinic(self):
        """Test get feedback by clinic."""
        report = clinics.RegionReport(kwargs={'pk': self.region.pk})
        report.get_object()
        feedback = report.get_feedback_by_clinic()
        self.assertEqual('TEST1', feedback[0][1])
        self.assertEqual(('Participation', '100.0%', 2), feedback[0][2][0])
        self.assertEqual(('Patient Satisfaction', '0.0%', 0), feedback[0][2][1])


class TestLGAReportFilterByService(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)
        self.clinic = factories.Clinic.create(code=1)
        self.patient = factories.Patient.create(serial='1111', clinic=self.clinic)

        self.facility = factories.SurveyQuestion.create(
            label='Open Facility',
            survey=self.survey,
            categories='Open\nClosed',
            primary_answer='Open',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=10)

        self.respect = factories.SurveyQuestion.create(
            label='Respectful Staff Treatment',
            survey=self.survey,
            categories='Yes\nNo',
            primary_answer='Yes',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=20)

        # Unfortunately, 'Wait Time' is compulsory so far...
        self.wait = factories.SurveyQuestion.create(
            label='Wait Time',
            survey=self.survey,
            categories='<1 hour\n1-2 hours\n2-4 hours\n>4 hours',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=30)

        service1 = factories.Service.create(code=1, name='Service 1')
        service2 = factories.Service.create(code=2, name='Service 2')

        v1 = factories.Visit.create(
            service=service1,
            visit_time=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=221)
        )
        v2 = factories.Visit.create(
            service=service2,
            visit_time=timezone.make_aware(timezone.datetime(2014, 8, 6), timezone.utc),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic, serial=111)
        )

        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            visit=v1,
            clinic=self.clinic, response='Yes')

        factories.SurveyQuestionResponse.create(
            question=self.facility,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 8), timezone.utc),
            visit=v2,
            clinic=self.clinic, response='Open')

        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 6), timezone.utc),
            visit=v2,
            clinic=self.clinic, response='Yes')

        self.wait_response = factories.SurveyQuestionResponse.create(
            question=self.wait,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 3), timezone.utc),
            visit=v2,
            clinic=self.clinic, response='<1 hour')

    def make_request(self, data=None):
        if data is None:
            data = {}
        url = '/lga_filter_feedback_by_service/'
        request = self.factory.get(url, data=data)
        return clinics.LGAReportFilterByService.as_view()(request)

    def test_request(self):
        data = {
            'start_date': 'August 01, 2014',
            'end_date': 'August 08, 2014'
        }
        response = self.make_request(data)
        self.assertEqual(response.status_code, 200)

    def test_get_feedback_data(self):
        start_date = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        end_date = timezone.make_aware(timezone.datetime(2014, 8, 8), timezone.utc)
        obj = clinics.LGAReportFilterByService()
        report = clinics.ReportMixin()
        data = obj.get_feedback_data(report, start_date, end_date)

        self.assertEqual('Service 1', data[0][0].name)
        self.assertEqual(
            [
                (u'Open Facility', None, 0),
                (u'Respectful Staff Treatment', None, 0),
                (u'Wait Time', None, 0)], data[0][1]
        )

        self.assertEqual('Service 2', data[1][0].name)
        self.assertEqual(
            [
                (u'Open Facility', '100.0%', 1),
                (u'Respectful Staff Treatment', '100.0%', 1),
                (u'Wait Time', u'<1 hr', 1)], data[1][1]
        )


class TestLGAReportFilterByClinic(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.survey = factories.Survey.create(role=survey_models.Survey.PATIENT_FEEDBACK)
        self.clinic1 = factories.Clinic.create(code=1, name='Clinic 1')
        self.clinic2 = factories.Clinic.create(code=2, name='Clinic 2')
        self.patient1 = factories.Patient.create(serial='1111', clinic=self.clinic1)
        self.patient2 = factories.Patient.create(serial='2222', clinic=self.clinic2)

        self.facility = factories.SurveyQuestion.create(
            label='Open Facility',
            survey=self.survey,
            categories='Open\nClosed',
            primary_answer='Open',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=10)

        self.respect = factories.SurveyQuestion.create(
            label='Respectful Staff Treatment',
            survey=self.survey,
            categories='Yes\nNo',
            primary_answer='Yes',
            for_satisfaction=True,
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            report_order=20)

        # Unfortunately, 'Wait Time' is compulsory so far...
        self.wait = factories.SurveyQuestion.create(
            label='Wait Time',
            survey=self.survey,
            categories='<1 hour\n1-2 hours\n2-4 hours\n>4 hours',
            question_type=survey_models.SurveyQuestion.MULTIPLE_CHOICE,
            for_satisfaction=True,
            last_negative=True,
            report_order=30)

        service1 = factories.Service.create(code=1, name='Service 1')

        v1 = factories.Visit.create(
            service=service1,
            visit_time=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic1, serial=221)
        )
        v2 = factories.Visit.create(
            service=service1,
            visit_time=timezone.make_aware(timezone.datetime(2014, 8, 6), timezone.utc),
            survey_sent=timezone.now(),
            patient=factories.Patient.create(clinic=self.clinic2, serial=111)
        )

        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.make_aware(timezone.datetime(2014, 7, 26), timezone.utc),
            visit=v1,
            clinic=self.clinic1, response='Yes')

        factories.SurveyQuestionResponse.create(
            question=self.facility,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 8), timezone.utc),
            visit=v2,
            clinic=self.clinic2, response='Open')

        factories.SurveyQuestionResponse.create(
            question=self.respect,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 6), timezone.utc),
            visit=v2,
            clinic=self.clinic2, response='Yes')

        self.wait_response = factories.SurveyQuestionResponse.create(
            question=self.wait,
            datetime=timezone.make_aware(timezone.datetime(2014, 8, 3), timezone.utc),
            visit=v2,
            clinic=self.clinic2, response='<1 hour')

    def make_request(self, data=None):
        if data is None:
            data = {}
        url = '/lga_filter_feedback_by_clinic/'
        request = self.factory.get(url, data=data)
        return clinics.LGAReportFilterByClinic.as_view()(request)

    def test_request(self):
        data = {
            'start_date': 'August 01, 2014',
            'end_date': 'August 08, 2014'
        }
        response = self.make_request(data)
        self.assertEqual(response.status_code, 200)

    def test_get_feedback_data(self):
        start_date = timezone.make_aware(timezone.datetime(2014, 8, 1), timezone.utc)
        end_date = timezone.make_aware(timezone.datetime(2014, 8, 8), timezone.utc)
        obj = clinics.LGAReportFilterByClinic()
        report = clinics.RegionReport()
        data = obj.get_feedback_data(report, start_date, end_date)

        self.assertEqual('Clinic 1', data[0][1])
        self.assertEqual(
            [
                (u'Participation', None, 0),
                (u'Patient Satisfaction', None, 0),
                (u'Quality', None, 0),
                (u'Quantity', None, 0),
                (u'Open Facility', None, 0),
                (u'Respectful Staff Treatment', None, 0),
                (u'Wait Time', None, 0)], data[0][2]
        )

        self.assertEqual('Clinic 2', data[1][1])
        self.assertEqual(
            [
                (u'Participation', '100.0%', 1),
                (u'Patient Satisfaction', '100.0%', 1),
                (u'Quality', None, 0),
                (u'Quantity', None, 0),
                (u'Open Facility', '100.0%', 1),
                (u'Respectful Staff Treatment', '100.0%', 1),
                (u'Wait Time', '<1 hr', 1)], data[1][2]
        )
