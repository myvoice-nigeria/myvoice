from django.test import TestCase

from .. import utils


class TestDisplayFeedback(TestCase):

    def test_false(self):
        bad_feedback = [None, '', '    ', ' 1', '1', 'yes', 'Yes', 'YES',
                        'no', 'No', 'NO', '55999']
        for bad in bad_feedback:
            self.assertEqual(utils.display_feedback(bad), False)

    def test_true(self):
        good_feedback = ['Yes this is good', 'Great feedback']
        for good in good_feedback:
            self.assertEqual(utils.display_feedback(good), True)
