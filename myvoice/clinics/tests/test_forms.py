import json

from django.test import TestCase

from myvoice.core.tests import factories

from .. import forms


class TestFeedbackForm(TestCase):
    """
    Requirements from TextIt Generic feedback flow
    Clinic ID comes as numeric category with label "Clinic".
    Clinic name (if clinic is not one of the options) comes as text with label "Which Clinic".
    General Feedback message comes as text with label "General Feedback".
    Any message that comes with category "Other" is ignored.

    More Assumptions:
    All clinic IDs configured in Textit have corresponding code in Clinic model.
    """

    def setUp(self):
        self.clinic = factories.Clinic.create(name='test', code=1)
        self.phone = "+12065551212"
        self.values = [
            {
                "category": "1",
                "text": "1",
                "value": "1",
                "label": "Clinic"
            },
            {
                "category": "All Responses",
                "text": "text",
                "value": "text",
                "label": "General Feedback"
            }
        ]

    def test_clinic(self):
        """Test that with Clinic and a numeric category, we return the Clinic
        and the General Feedback message."""
        values = [
            {"category": "1", "value": "1", "label": "Clinic"},
            {"category": "All Responses", "value": "text", "label": "General Feedback"},
        ]
        json_data = json.dumps(values)
        data = {"phone": self.phone, "values": json_data}
        form = forms.FeedbackForm(data)

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['values']['clinic'], self.clinic)
        self.assertEqual(form.cleaned_data['values']['message'], 'text')
        self.assertEqual(form.cleaned_data['phone'], '+12065551212')

    def test_which_clinic(self):
        """Test that with "Which Clinic", we return None for Clinic and a concat
        of Which Clinic value and message value."""
        values = [
            {"category": "Other", "value": "1", "label": "Clinic"},
            {"category": "Other", "value": "9", "label": "Clinic"},
            {"category": "All Responses", "value": "9", "label": "Which Clinic"},
            {"category": "All Responses", "value": "no", "label": "General Feedback"},
        ]
        json_data = json.dumps(values)
        data = {"phone": self.phone, "values": json_data}
        form = forms.FeedbackForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['values']['clinic'], None)
        self.assertEqual(form.cleaned_data['values']['message'], 'no (9)')
