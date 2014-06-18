import datetime

from django.test import TestCase

from myvoice.core.tests import factories

from .. import forms
from .. import statistics


class TestClinicStatisticAdminForm(TestCase):
    Form = forms.ClinicStatisticAdminForm
    Factory = factories.ClinicStatistic

    def setUp(self, **kwargs):
        super(TestClinicStatisticAdminForm, self).setUp()
        self.data = {
            'clinic': factories.Clinic().pk,
            'statistic': statistics.INCOME,  # statistics.INTEGER
            'month': datetime.date.today().isoformat(),
            'value': 123,
        }

    def test_create_initial_value(self):
        """Initial value should be empty when creating a statistic."""
        form = self.Form()
        self.assertEqual(form.fields['value'].initial, None)

    def test_edit_initial_value(self):
        """Initial value should be populated when editing a statistic."""
        instance = self.Factory()
        form = self.Form(instance=instance)
        self.assertEqual(form.fields['value'].initial, instance.value)

    def test_create_valid_value(self):
        """Should be able to create a new statistic from a valid form."""
        form = self.Form(data=self.data)
        self.assertTrue(form.is_valid())

        obj = form.save()
        self.assertEqual(obj.clinic.pk, self.data['clinic'])
        self.assertEqual(obj.statistic, self.data['statistic'])
        self.assertEqual(obj.month.isoformat(), self.data['month'])
        self.assertEqual(obj.value, self.data['value'])

    def test_edit_valid_value(self):
        """Should be able to edit an existing statistic from a valid form."""
        instance = self.Factory()
        form = self.Form(instance=instance, data=self.data)
        self.assertTrue(form.is_valid())

        obj = form.save()
        self.assertEqual(obj.pk, instance.pk)
        self.assertEqual(obj.clinic.pk, self.data['clinic'])
        self.assertEqual(obj.statistic, self.data['statistic'])
        self.assertEqual(obj.month.isoformat(), self.data['month'])
        self.assertEqual(obj.value, self.data['value'])

    def test_create_invalid_value(self):
        """Form is invalid if value of wrong type is provided."""
        self.data['value'] = 'invalid'
        form = self.Form(data=self.data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('value' in form.errors)

    def test_edit_invalid_value(self):
        """Form is invalid if value of wrong type is provided."""
        self.data['value'] = 'invalid'
        instance = self.Factory()
        form = self.Form(instance=instance, data=self.data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('value' in form.errors)

    def test_create_no_value(self):
        """Form is invalid if no value is provided."""
        self.data.pop('value')
        form = self.Form(data=self.data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('value' in form.errors)

    def test_edit_no_value(self):
        """Form is invalid if no value is provided."""
        self.data.pop('value')
        instance = self.Factory()
        form = self.Form(instance=instance, data=self.data)
        self.assertFalse(form.is_valid())
        self.assertEqual(len(form.errors), 1)
        self.assertTrue('value' in form.errors)
