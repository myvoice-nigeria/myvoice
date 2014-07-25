from django.test import TestCase

from .. import utils

from myvoice.core.tests import factories


class TestDisplayFeedback(TestCase):

    def test_false(self):
        bad_feedback = [None, '', '    ', ' 1', '1', 'yes', 'Yes', 'YES',
                        'no', 'No', 'NO', '55999', 'n0']
        for bad in bad_feedback:
            self.assertEqual(utils.display_feedback(bad), False)

    def test_true(self):
        good_feedback = ['Yes this is good', 'Great feedback', '20']
        for good in good_feedback:
            self.assertEqual(utils.display_feedback(good), True)


class TestSurveyUtils(TestCase):

    def setUp(self):
        self.survey = factories.Survey.create()
        self.question = factories.SurveyQuestion.create(survey=self.survey)
        self.responses = [factories.SurveyQuestionResponse.create(
            response=ans, question=self.question)
            for ans in ('Yes', 'Yes', 'Yes', 'No')]

    def test_analyze(self):
        """Test it returns percentage of responses with a given answer."""
        self.assertEqual(75, utils.analyze(self.responses, 'Yes'))
        self.assertEqual(25, utils.analyze(self.responses, 'No'))

    def test_get_mode(self):
        """Test that get_mode function finds the most common item."""
        for i in range(3):
            self.responses.append(factories.SurveyQuestionResponse.create(
                response='No', question=self.question))
        self.assertEqual('No', utils.get_mode(self.responses))

    def test_get_mode_acceptable_answers(self):
        """Test that get_mode respects acceptable answers."""
        for i in range(3):
            self.responses.append(factories.SurveyQuestionResponse.create(
                response='Maybe', question=self.question))
        self.assertEqual(
            'Maybe', utils.get_mode(self.responses, acceptable_answers=['No', 'Maybe']))
