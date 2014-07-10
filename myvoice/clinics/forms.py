from django import forms

import json
import re

from . import models


VISIT_EXPR = '''
^                               # Start
\s*                             # Leading whitespace
(i|I|\d)+                       # Numbers as clinic
(\s|\*)+                        # Whitespace or '*'
((1|i|I)|((i|I|o|O|[0-9])+))    # Either 1 or numbers as mobile
(\s|\*)+                        # Whitespace or '*'
(i|I|o|O|[0-9])+                # Numbers as serial
(\s|\*)+                        # Whitespace or '*'
(i|I|o|O|[0-9])+                # Numbers as Service
\s*                             # Trailing whitespace
$                               # End
'''
VISIT_PATT = re.compile(VISIT_EXPR, re.VERBOSE)


class VisitForm(forms.Form):
    phone = forms.CharField(max_length=20)
    text = forms.RegexField(VISIT_PATT, max_length=200, error_messages={
        'invalid': '1 or more parts of your entry are missing, please check and '
        'enter the registration again.'})

    serial_min = 3
    serial_max = 6

    def __init__(self, *args, **kwargs):
        super(VisitForm, self).__init__(*args, **kwargs)
        self.error_list = []

    def replace_alpha(self, text):
        """Convert 'o' and 'O' to '0', and 'i', 'I' to '1'."""
        return text.replace('o', '0').replace('O', '0').replace('i', '1').replace(
            'I', '1').replace('*', ' ')

    def clean_text(self):
        """Validate input text.

        text is in format: CLINIC MOBILE SERIAL SERVICE
        """
        # How come this is available here?
        sender = self.cleaned_data['phone']

        cleaned_data = self.replace_alpha(self.cleaned_data['text'].strip())
        clnc, mobile, serial, srvc = cleaned_data.split()

        # Check if mobile is correct
        if len(mobile) not in [1, 11]:
            self.error_list.append('mobile')

        # Check if clinic is valid
        try:
            clinic = models.Clinic.objects.get(code=clnc)
        except (models.Clinic.DoesNotExist, ValueError):
            self.error_list.append('clinic')
            clinic = None

        # Check if serial is valid
        if len(serial) < self.serial_min or len(serial) > self.serial_max:
            self.error_list.append('serial')

        # Check if Service is valid
        try:
            service = models.Service.objects.get(code=srvc)
        except models.Service.DoesNotExist:
            self.error_list.append('service')
            service = None

        # Check if there are errors.
        # If 2 previous validation errors exist, allow entry to pass
        # As long as mobile is ok.
        if len(self.error_list) > 0:
            fld_list = ', '.join(self.error_list).upper()
            if models.VisitRegistrationError.objects.filter(
                    sender=sender).count() >= 2 and 'mobile' not in self.error_list:
                # Save error log
                models.VisitRegistrationErrorLog.objects.create(
                    sender=sender,
                    error_type=fld_list,
                    message=self.cleaned_data['text'])
                # Clear Current Error state
                models.VisitRegistrationError.objects.filter(
                    sender=sender).delete()
            else:
                # Save error state
                models.VisitRegistrationError.objects.create(sender=sender)
                error_msg = 'Error for serial {0}. There is a mistake in '\
                    '{1}. Please check and enter the whole registration '\
                    'code again.'.format(serial, fld_list)
                raise forms.ValidationError(error_msg)

        return clinic, mobile, serial, service, self.cleaned_data['text']


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
