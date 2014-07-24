import json

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

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
        self.error_msg = 'Error for serial {}. There was a mistake in entering '\
            '{}. Please check and enter the whole registration code again.'

    def test_visit(self):
        """Test that clean_text returns tuple of:
            clinic, phone, serial, service, input text."""
        data = {'text': '1 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(self.clinic, form.cleaned_data['text'][0])
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertEqual('4000', form.cleaned_data['text'][2])
        self.assertEqual(self.service, form.cleaned_data['text'][3])

    def test_wrong_clinic(self):
        """Test that wrong clinic raises error."""
        data = {'text': '12 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

        # Check error message
        error_msg = self.error_msg.format(4000, 'CLINIC')
        self.assertEqual(error_msg, form.errors['text'][0])

    def test_invalid_alpha_clinic(self):
        """Test that alphabetical clinic raises error."""
        data = {'text': 'A 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

        # Check error message
        error_msg = '1 or more parts of your entry are missing, please check '\
                    'and enter the registration again.'
        self.assertEqual(error_msg, form.errors['text'][0])

    def test_wrong_data_twice_validates(self):
        """Test that wrong data after 2 previous error validates."""
        # 1st time, Clinic is wrong
        data1 = {'text': '12 08122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data1)
        # So first clean is run
        form.is_valid()
        self.assertFalse(form.is_valid())

        # 2nd time, Service is wrong
        data2 = {'text': '1 08122233301 4000 50', 'phone': '+2348022112211'}
        form = forms.VisitForm(data2)
        self.assertFalse(form.is_valid())

        # 3rd time, Service is wrong
        data2 = {'text': '1 08122233301 4000 50', 'phone': '+2348022112211'}
        form = forms.VisitForm(data2)
        self.assertTrue(form.is_valid())

    def test_wrong_mobile(self):
        """Test that wrong mobile does not validate."""
        data = {'text': 'A 8122233301 4000 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

    def test_wrong_serial(self):
        """Test that invalid serial does not validate."""
        data = {'text': '1 08122233301 4 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

        # Check error message
        error_msg = self.error_msg.format(4, 'SERIAL')
        self.assertEqual(error_msg, form.errors['text'][0])

    def test_wrong_service(self):
        """Test that invalid service does not validate."""
        data = {'text': '1 08122233301 400 50', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

        # Check error message
        error_msg = self.error_msg.format(400, 'SERVICE')
        self.assertEqual(error_msg, form.errors['text'][0])

    def test_wrong_service_and_clinic(self):
        """Test that invalid service does not validate."""
        data = {'text': '21 08122233301 400 50', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

        # Check error message
        error_msg = self.error_msg.format(400, 'CLINIC, SERVICE')
        self.assertEqual(error_msg, form.errors['text'][0])

    def test_valid_alpha_clinic(self):
        """Test that 'i' and 'I' are interpreted as 1 in clinic."""
        data = {'text': 'i 08122233301 400 5', 'phone': '+2348022112211'}
        form1 = forms.VisitForm(data)
        self.assertTrue(form1.is_valid())
        self.assertEqual(self.clinic, form1.cleaned_data['text'][0])

        data = {'text': 'I 08122233301 400 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(self.clinic, form.cleaned_data['text'][0])

    def test_double_alpha_clinics(self):
        """Test that 'ii' and 'II' are interpreted as 11 in clinic."""
        clinic = factories.Clinic.create(code=11)
        data = {'text': 'ii 08122233301 400 5', 'phone': '+2348022112211'}
        form1 = forms.VisitForm(data)
        self.assertTrue(form1.is_valid())
        self.assertEqual(clinic, form1.cleaned_data['text'][0])

        data = {'text': 'II 08122233301 400 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(clinic, form.cleaned_data['text'][0])

    def test_valid_alpha_mobile(self):
        """Test that 'i' and 'I' are interpreted as 1 in mobile."""
        data = {'text': '1 08i2223330I 400 5', 'phone': '+2348022112211'}
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

    def test_serial_startwith_0(self):
        """Test that serials starting with '0' are valid."""
        data = {'text': '1 08122233301 0401 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual('08122233301', form.cleaned_data['text'][1])
        self.assertTrue(self.clinic, form.cleaned_data['text'][0])
        self.assertTrue('0401', form.cleaned_data['text'][2])
        self.assertTrue('5', form.cleaned_data['text'][3])

    def test_missing_field(self):
        """Test that missing field returns proper message."""
        data = {'text': '08122233301 0401 5', 'phone': '+2348022112211'}
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())
        error_msg = '1 or more parts of your entry are missing, please check and '\
                    'enter the registration again.'
        self.assertEqual(error_msg, form.errors['text'][0])

    def test_same_visit_too_soon(self):
        """Test that registering 2nd visit with same clinic, mobile, serial
        and time difference is < 30 mins is invalid."""
        data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        factories.Visit.create(
            patient=factories.Patient.create(clinic=self.clinic, serial='4001'),
            mobile='08122233301',
            visit_time=timezone.now()-timedelta(minutes=29))
        form = forms.VisitForm(data)
        self.assertFalse(form.is_valid())

        # Check Error message is correct
        error_msg = "This registration was received before. Thank you."
        self.assertEqual(error_msg, form.errors['text'][0])

    def test_same_visit_after_30_mins(self):
        """Test that registering 2nd visit with same clinic, mobile, serial
        and time difference is > 30 mins is valid."""
        data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        factories.Visit.create(
            patient=factories.Patient.create(clinic=self.clinic, serial='4001'),
            mobile='08122233301',
            visit_time=timezone.now()-timedelta(minutes=31))
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())

    def test_same_patient_different_clinic(self):
        """Test that registering 2nd visit with same mobile, serial but different
        clinic is valid even if time difference is < 30 mins."""
        data = {'text': '1 08122233301 4001 5', 'phone': '+2348022112211'}
        factories.Visit.create(
            patient=factories.Patient.create(
                clinic=factories.Clinic.create(code=5), serial='4001'),
            mobile='08122233301',
            visit_time=timezone.now()-timedelta(minutes=9))
        form = forms.VisitForm(data)
        self.assertTrue(form.is_valid())
