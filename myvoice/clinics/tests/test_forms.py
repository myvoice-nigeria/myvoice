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


class TestVisitForm(TestCase):

    def setUp(self):
        self.service = factories.Service.create(code=5)
        self.clinic = factories.Clinic.create(code=1)

    def test_visit(self):
        """Test that clean_text returns tuple of:
            clinic, phone, serial, service, input text."""
        data = {'text': '1 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(self.clinic, form.cleaned_data['text'][0])
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertEqual('4000', form.cleaned_data['text'][2])
        self.assertEqual('5', form.cleaned_data['text'][3])

    def test_wrong_clinic(self):
        """Test that wrong clinic raises error."""
        data = {'text': '12 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

    def test_invalid_alpha_clinic(self):
        """Test that wrong clinic raises error."""
        data = {'text': 'A 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

    def test_wrong_clinic_twice_validates(self):
        """Test that wrong clinic after previous error validates."""
        data = {'text': '12 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        # So first clean is run
        form.is_valid()
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())

    def test_wrong_mobile(self):
        """Test that wrong mobile raises error."""
        data = {'text': 'A 8122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

    def test_invalid_serial_validate(self):
        """Test that invalid serial will still validate."""
        data = {'text': '1 08122233301 4 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())

    def test_valid_alpha_clinic(self):
        """Test that 'i' and 'I' are interpreted as 1 in clinic."""
        data = {'text': 'i 08122233301 4 5', 'phone': '+2348022112211'}
        form1 = forms.VisitForm(data)
        self.assertTrue(form1.is_valid())
        self.assertEqual(self.clinic, form1.cleaned_data['text'][0])

        data = {'text': 'I 08122233301 4 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(self.clinic, form.cleaned_data['text'][0])

    def test_double_alpha_clinics(self):
        """Test that 'ii' and 'II' are interpreted as 11 in clinic."""
        clinic = factories.Clinic.create(code=11)
        data = {'text': 'ii 08122233301 4 5', 'phone': '+2348022112211'}
        form1 = forms.VisitForm(data)
        self.assertTrue(form1.is_valid())
        self.assertEqual(clinic, form1.cleaned_data['text'][0])

        data = {'text': 'II 08122233301 4 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(clinic, form.cleaned_data['text'][0])

    def test_valid_alpha_mobile(self):
        """Test that 'i' and 'I' are interpreted as 1 in mobile."""
        data = {'text': '1 08i2223330I 4 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])

    def test_newline_as_whitespace(self):
        """Test that \n is interpreted as <space>."""
        data = {'text': '1\n08122233301\n401\n5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertTrue(self.clinic, form.cleaned_data['text'][0])
        self.assertTrue('401', form.cleaned_data['text'][2])
        self.assertTrue('5', form.cleaned_data['text'][3])

    def test_multiple_whitespace(self):
        """Test that up to 3 whitespaces are treated as one."""
        data = {'text': '1\n  08122233301 \n 401   5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertTrue(self.clinic, form.cleaned_data['text'][0])
        self.assertTrue('401', form.cleaned_data['text'][2])
        self.assertTrue('5', form.cleaned_data['text'][3])

    def test_asterisk_as_whitespace(self):
        """Test that '*' is treated as whitespace."""
        data = {'text': '1*08122233301*401*5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertTrue(self.clinic, form.cleaned_data['text'][0])
        self.assertTrue('401', form.cleaned_data['text'][2])
        self.assertTrue('5', form.cleaned_data['text'][3])

    def test_asterisk_whitespace_mix(self):
        """Test that '*' mixed with '\n' and <space> is treated as whitespace."""
        data = {'text': '1 * 08122233301\n* 401\n*\n5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertTrue(self.clinic, form.cleaned_data['text'][0])
        self.assertTrue('401', form.cleaned_data['text'][2])
        self.assertTrue('5', form.cleaned_data['text'][3])

    def test_leading_whitespace(self):
        """Test that leading whitespace is removed."""
        data = {'text': ' 1 * 08122233301\n* 401\n*\n5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertTrue(self.clinic, form.cleaned_data['text'][0])
        self.assertTrue('401', form.cleaned_data['text'][2])
        self.assertTrue('5', form.cleaned_data['text'][3])

    def test_trailing_whitespace(self):
        """Test that trailing whitespace is removed."""
        data = {'text': '1 * 08122233301\n* 401\n*\n5\n ', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertTrue(self.clinic, form.cleaned_data['text'][0])
        self.assertTrue('401', form.cleaned_data['text'][2])
        self.assertTrue('5', form.cleaned_data['text'][3])
