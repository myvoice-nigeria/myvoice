from django import forms

import json

from . import models


class ClinicStatisticAdminForm(forms.ModelForm):
    """
    ClinicStatistic add/edit form which chooses the underlying field
    (text_value, int_value, or float_value) that will hold the statistic's
    value.
    """
    value = forms.CharField(label='Value', required=True, max_length=255)

    class Meta:
        model = models.ClinicStatistic

    def __init__(self, *args, **kwargs):
        super(ClinicStatisticAdminForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            # We are editing an instance; show its value in initial data.
            self.fields['value'].initial = self.instance.value

    def _post_clean(self):
        """Set the instance value and validate it."""
        # Must call super first, to update the other fields of the form's
        # instance.
        super(ClinicStatisticAdminForm, self)._post_clean()
        if 'value' in self.cleaned_data:
            self.instance.value = self.cleaned_data['value']
            try:
                self.instance.clean_value()
            except forms.ValidationError as e:
                self._update_errors(e)
        else:
            # Standard form validation will display the error that this
            # field is required.
            pass


class VisitForm(forms.Form):
    phone = forms.CharField(max_length=20)
    text = forms.RegexField(
        '^(i|I|\d+)\s+((1|i|I)|((i|I|o|O|[0-9])+))\s+(i|I|o|O|[0-9])+\s+(i|I|o|O|[0-9])+$',
        max_length=50,
        error_messages={'invalid': 'Your message is invalid. Please retry'})

    def replace_alpha(self, text):
        """Convert 'o' and 'O' to '0', and 'i', 'I' to '1'."""
        return text.replace('o', '0').replace('O', '0').replace('i', '1').replace('I', '1')

    def clean_text(self):
        """Validate input text.

        text is in format: CLINIC PHONE SERIAL SERVICE
        """
        clnc, phone, serial, srvc = [
            self.replace_alpha(i) for i in self.cleaned_data['text'].split()]

        # Check if mobile is correct
        if len(phone) not in [1, 11]:
            error_msg = 'Mobile number incorrect for patient with serial {serial}. Must '\
                        'be 11 digits with no spaces. Please check your instruction card '\
                        'and re-enter the entire patient code in 1 text.'
            raise forms.ValidationError(error_msg.format(serial=serial))
        # Check if clinic is valid
        try:
            clinic = models.Clinic.objects.get(code=clnc)
        except (models.Clinic.DoesNotExist, ValueError):
            error_msg = 'Clinic number incorrect. Must be 1-11, please check your '\
                        'instruction card and re-enter the entire patient code in 1 sms'
            # If ValidationError exists don't raise error but send "empty" clinic
            if models.VisitRegistrationError.objects.filter(sender=phone).count():
                clinic = None
                # Clear VisitRegistrationError
                models.VisitRegistrationError.objects.filter(sender=phone).delete()
            else:
                models.VisitRegistrationError.objects.create(sender=phone)
                raise forms.ValidationError(error_msg)
        else:
            models.VisitRegistrationError.objects.filter(sender=phone).delete()

        return clinic, phone, serial, srvc, self.cleaned_data['text']


class SelectClinicForm(forms.Form):
    clinic = forms.ModelChoiceField(queryset=None)

    def __init__(self, *args, **kwargs):
        super(SelectClinicForm, self).__init__(*args, **kwargs)
        self.fields['clinic'].queryset = models.Clinic.objects.order_by('name')


class FeedbackForm(forms.Form):
    """
    Requirements from TextIt Generic feedback flow
    Clinic ID response come as numeric category with label "Clinic".
    Clinic name (if clinic is not sent) comes as text with label "Which Clinic".
    Complaint message comes as text with label "General Feedback".
    Any message that comes with category "Other" is ignored.

    More:
    Clinics configured in Textit flow have corresponding code in Clinic model.
    """
    phone = forms.CharField(max_length=20)
    values = forms.CharField()

    def clean_values(self):
        """Return Clinic and Message."""
        data = self.cleaned_data['values'].replace('+', ' ')
        values = json.loads(data)

        clinic = None
        clinic_text = ''
        message = ''

        for item in values:
            category = item.get('category').lower()
            label = item.get('label').lower()
            value = item.get('value')

            if category == 'other':
                continue
            elif label == 'general feedback':
                message = value
            elif label == 'clinic':
                clinic = models.Clinic.objects.get(code=category)
            elif label == 'which clinic':
                clinic_text = value

        if clinic_text:
            message += ' ({})'.format(clinic_text)
        return {'clinic': clinic, 'message': message}
