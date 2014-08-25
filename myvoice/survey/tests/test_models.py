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

    def test_unicode(self):
        """Smoke test for string representation."""
        obj = self.Factory.create(response='test', question=self.question)
        self.assertEqual('test', str(obj))

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


class TestSurveyResponseVisit(TestCase):
    """Test saving survey question response affects visit indices."""

    def setUp(self):
        self.survey = factories.Survey(role=models.Survey.PATIENT_FEEDBACK)
        # self.question = factories.SurveyQuestion.create(
        #     survey=self.survey, label='Test1', categories="Yes\nNo")
        self.visit = factories.Visit.create()

    def test_satisfaction(self):
        """Test that patient satisfaction is determined properly."""
        visit1 = factories.Visit.create()
        visit2 = factories.Visit.create()
        question = factories.SurveyQuestion.create(
            survey=self.survey, for_satisfaction=True, label='Test', categories="Yes\nNo")

        factories.SurveyQuestionResponse.create(
            question=question, response='Yes', visit=visit1)
        self.assertTrue(visit1.satisfied)

        factories.SurveyQuestionResponse.create(
            question=question, response='No', visit=visit2)
        self.assertFalse(visit2.satisfied)

    def test_satisfaction_alread_negative(self):
        """Test that patient satisfaction is not changed if already dis-satisfied."""
        visit = factories.Visit.create(satisfied=False)
        question = factories.SurveyQuestion.create(
            survey=self.survey, for_satisfaction=True, label='Test', categories="Yes\nNo")
        factories.SurveyQuestionResponse.create(
            question=question, response='Yes', visit=visit)
        self.assertFalse(visit.satisfied)

    def test_satisfaction_last_negative(self):
        """Test that patient satisfaction is determined properly
        for questions whose answers are all positive save the last one."""
        visit1 = factories.Visit.create()
        visit2 = factories.Visit.create()
        visit3 = factories.Visit.create()
        question = factories.SurveyQuestion.create(
            survey=self.survey,
            for_satisfaction=True,
            label='Test',
            last_negative=True,
            categories="Yes\nmaybe\nno")

        factories.SurveyQuestionResponse.create(
            question=question, response='Yes', visit=visit1)
        self.assertTrue(visit1.satisfied)

        factories.SurveyQuestionResponse.create(
            question=question, response='maybe', visit=visit2)
        self.assertTrue(visit2.satisfied)

        factories.SurveyQuestionResponse.create(
            question=question, response='no', visit=visit3)
        self.assertFalse(visit3.satisfied)

    def test_participation(self):
        """Test that patient survey participation is saved properly."""
        visit1 = factories.Visit.create()
        question = factories.SurveyQuestion.create(
            survey=self.survey, label='Test')

        factories.SurveyQuestionResponse.create(
            question=question, response='no', visit=visit1)
        self.assertTrue(visit1.survey_started)

    def test_completion(self):
        """Test that patient survey completion is saved properly."""
        visit1 = factories.Visit.create()
        visit2 = factories.Visit.create()
        question1 = factories.SurveyQuestion.create(
            survey=self.survey, label='Test')
        question2 = factories.SurveyQuestion.create(
            survey=self.survey, last_required=True, label='Test1')

        factories.SurveyQuestionResponse.create(
            question=question1, response='no', visit=visit1)
        factories.SurveyQuestionResponse.create(
            question=question2, response='no', visit=visit2)

        self.assertFalse(visit1.survey_completed)
        self.assertTrue(visit2.survey_completed)
