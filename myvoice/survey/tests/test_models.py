from django.test import TestCase

from myvoice.core.tests import factories

from .. import models


class TestDisplayLabel(TestCase):
    Model = models.DisplayLabel
    Factory = factories.DisplayLabel

    def test_unicode(self):
        """Smoke test for string representation."""
        obj = self.Factory.create(name='Test')
        self.assertEqual(str(obj), 'Test')


class TestSurveyQuestionResponse(TestCase):
    Model = models.SurveyQuestionResponse
    Factory = factories.SurveyQuestionResponse

    def setUp(self):
        self.survey = factories.Survey(role=models.Survey.PATIENT_FEEDBACK)
        self.question = factories.SurveyQuestion.create(
            survey=self.survey, label='Test', categories="Yes\nNo")

    def test_positive_response(self):
        """Test that positive response is saved for correct answer."""
        response = factories.SurveyQuestionResponse.create(
            question=self.question,
            response='Yes')

        self.assertTrue(response.positive_response)

    def test_negative_response(self):
        """Test that positive response is not saved for wrong answer."""
        response = factories.SurveyQuestionResponse.create(
            question=self.question,
            response='No')

        self.assertIsNone(response.positive_response)

    def test_last_negative(self):
        """Test that positive response is saved for last negatives too."""
        question = factories.SurveyQuestion.create(
            survey=self.survey,
            label='Test1',
            last_negative=True,
            categories="one\ntwo\nthree\nbad")
        response1 = factories.SurveyQuestionResponse.create(
            question=question,
            response='three')

        self.assertTrue(response1.positive_response)

        response2 = factories.SurveyQuestionResponse.create(
            question=question,
            response='bad')

        self.assertIsNone(response2.positive_response)
