import mock

from django.test import TestCase
from django.utils import timezone
from django.test.utils import override_settings

from myvoice.clinics.models import Visit
from myvoice.core.tests import factories

from .. import tasks
from .. import models
from ..textit import TextItException


@override_settings(TEXTIT_API_TOKEN='dummy test token')
@mock.patch('myvoice.survey.tasks.importer.import_responses')
class TestImportResponses(TestCase):

    def test_active_survey(self, import_responses):
        """We should call the import_responses utility for active surveys."""
        self.survey = factories.Survey(active=True)
        tasks.import_responses()
        self.assertEqual(import_responses.call_count, 1)
        self.assertEqual(import_responses.call_args, ((self.survey.flow_id,),))

    def test_inactive_survey(self, import_responses):
        """We should not try to import responses for inactive surveys."""
        self.survey = factories.Survey(active=False)
        tasks.import_responses()
        self.assertEqual(import_responses.call_count, 0)


@override_settings(TEXTIT_API_TOKEN='dummy test token')
@mock.patch.object(tasks.TextItApi, 'start_flow')
class TestStartFeedbackSurvey(TestCase):

    def setUp(self):
        super(TestStartFeedbackSurvey, self).setUp()
        self.survey = factories.Survey(role=models.Survey.PATIENT_FEEDBACK)
        self.visit = factories.Visit()

    def test_no_such_survey(self, start_flow):
        """No flow should be started if there is no patient feedback survey."""
        self.survey.delete()
        tasks.start_feedback_survey(self.visit.pk)
        self.assertEqual(start_flow.call_count, 0)
        self.visit = Visit.objects.get(pk=self.visit.pk)
        self.assertIsNone(self.visit.survey_sent)

    def test_no_such_visit(self, start_flow):
        """No flow should be started if there is no associated visit."""
        tasks.start_feedback_survey(12345)
        self.assertEqual(start_flow.call_count, 0)
        self.visit = Visit.objects.get(pk=self.visit.pk)
        self.assertIsNone(self.visit.survey_sent)

    def test_start_flow(self, start_flow):
        """When survey is sent, survey_sent field should be updated."""
        tasks.start_feedback_survey(self.visit.pk)
        self.assertEqual(start_flow.call_count, 1)
        expected = ((self.survey.flow_id, self.visit.patient.mobile),)
        self.assertEqual(start_flow.call_args, expected)
        self.visit = Visit.objects.get(pk=self.visit.pk)
        self.assertIsNotNone(self.visit.survey_sent)

    def test_error(self, start_flow):
        """If error occurs during start_flow, survey_sent should be null."""
        start_flow.side_effect = TextItException
        tasks.start_feedback_survey(self.visit.pk)
        self.assertEqual(start_flow.call_count, 1)
        expected = ((self.survey.flow_id, self.visit.patient.mobile),)
        self.assertEqual(start_flow.call_args, expected)
        self.visit = Visit.objects.get(pk=self.visit.pk)
        self.assertIsNone(self.visit.survey_sent)


@override_settings(TEXTIT_API_TOKEN='dummy test token')
@mock.patch.object(tasks.TextItApi, 'send_message')
@mock.patch('myvoice.survey.tasks.start_feedback_survey.apply_async')
class TestHandleNewVisits(TestCase):

    def setUp(self):
        super(TestHandleNewVisits, self).setUp()
        self.survey = factories.Survey(role=models.Survey.PATIENT_FEEDBACK)

    def test_new_visit(self, send_message, start_feedback_survey):
        """
        We should send a welcome message and schedule the survey to be started
        for a new visit.
        """
        visit = factories.Visit(welcome_sent=None)
        tasks.handle_new_visits()
        self.assertEqual(send_message.call_count, 1)
        self.assertEqual(send_message.call_args, ((visit.patient.mobile,),))
        visit = Visit.objects.get(pk=visit.pk)
        self.assertIsNotNone(visit.welcome_sent)
        self.assertEqual(start_feedback_survey.call_count, 1)

    def test_past_visit(self, send_message, start_feedback_survey):
        """
        We should not do anything for visits that have already had the
        welcome message sent.
        """
        welcome_sent = timezone.now()
        visit = factories.Visit(welcome_sent=welcome_sent)
        tasks.handle_new_visits()
        self.assertEqual(send_message.call_count, 0)
        self.assertEqual(start_feedback_survey.call_count, 0)
        visit = Visit.objects.get(pk=visit.pk)
        self.assertEqual(visit.welcome_sent, welcome_sent)
        self.assertIsNone(visit.survey_sent)
