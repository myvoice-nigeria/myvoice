from django.test import TestCase

from .. import utils
from .. import models as survey_models

from myvoice.core.tests import factories

from operator import itemgetter


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
        self.question = factories.SurveyQuestion.create(survey=self.survey, label='Test')
        self.responses = [factories.SurveyQuestionResponse.create(
            response=ans, question=self.question)
            for ans in ('Yes', 'Yes', 'Yes', 'No')]
        self.answers = [r.response for r in self.responses]

    def test_analyze(self):
        """Test it returns percentage of responses with a given answer."""
        self.assertEqual(75, utils.analyze(self.answers, 'Yes'))
        self.assertEqual(25, utils.analyze(self.answers, 'No'))
        self.assertEqual(None, utils.analyze([], 'Yes'))

    def test_get_mode(self):
        """Test that get_mode function finds the most common item."""
        for i in range(3):
            self.responses.append(factories.SurveyQuestionResponse.create(
                response='No', question=self.question))
        answers = [r.response for r in self.responses]
        self.assertEqual('No', utils.get_mode(answers))
        self.assertEqual(None, utils.get_mode([]))

    def test_get_mode_acceptable_answers(self):
        """Test that get_mode respects acceptable answers."""
        # So we have 4 'Yes' and only 3 'Maybe'
        self.responses.append(factories.SurveyQuestionResponse.create(
            response='Yes', question=self.question))
        for i in range(3):
            self.responses.append(factories.SurveyQuestionResponse.create(
                response='Maybe', question=self.question))
        answers = [r.response for r in self.responses]
        self.assertEqual(
            'Maybe', utils.get_mode(answers, acceptable_answers=['No', 'Maybe']))

    def test_get_mode_rename_hour_to_hr(self):
        """Test that get_mode renames hour to hr."""
        self.responses.append(factories.SurveyQuestionResponse.create(
            response='2 hours', question=self.question))
        answers = ['2 hours', '2 hours', '1 hour']
        self.assertEqual(
            '2 hrs', utils.get_mode(answers, acceptable_answers=['2 hours', '1 hour']))

    def test_group_responses(self):
        """Test group_responses."""
        question = factories.SurveyQuestion.create(survey=self.survey, label='Test1')
        for i in range(3):
            self.responses.append(factories.SurveyQuestionResponse.create(
                response='Maybe', question=question))
        grouped_responses = utils.group_responses(self.responses, 'question.label')
        self.assertEqual(2, len(grouped_responses))

        # Test the content of each group
        grouped_dict = dict(grouped_responses)
        self.assertEqual(4, len(grouped_dict['Test']))
        self.assertEqual(3, len(grouped_dict['Test1']))

    def test_group_responses_valuesqset(self):
        """Test group_responses with ValuesQueryset."""
        question = factories.SurveyQuestion.create(survey=self.survey, label='Test1')
        for i in range(3):
            self.responses.append(factories.SurveyQuestionResponse.create(
                response='Maybe', question=question))

        responses = survey_models.SurveyQuestionResponse.objects.values(
            'question__label', 'response')
        grouped_responses = utils.group_responses(responses, 'question__label', keyfunc=itemgetter)
        self.assertEqual(2, len(grouped_responses))

        # Test the content of each group
        grouped_dict = dict(grouped_responses)
        self.assertEqual(4, len(grouped_dict['Test']))
        self.assertEqual(3, len(grouped_dict['Test1']))

    def test_convert_local_format(self):
        """Test conversion of phone number to local format."""
        self.assertEqual('08111111111', utils.convert_to_local_format('08111111111'))
        self.assertEqual('08111111111', utils.convert_to_local_format('+2348111111111'))
        self.assertEqual('08111111111', utils.convert_to_local_format('2348111111111'))
        self.assertEqual(None, utils.convert_to_local_format('234811111111122'))

    def test_convert_international_format(self):
        """Test conversion of phone number to international format."""
        self.assertEqual('+2348111111111', utils.convert_to_international_format('+2348111111111'))
        self.assertEqual('+2348111111111', utils.convert_to_international_format('2348111111111'))
        self.assertEqual('+2348111111111', utils.convert_to_international_format('08111111111'))
        self.assertEqual(None, utils.convert_to_international_format('0811111'))
