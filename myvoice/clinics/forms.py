from django import forms
from django.utils import timezone

import json
import re
from datetime import timedelta
import logging

from . import models

from myvoice.survey import utils as survey_utils

logger = logging.getLogger(__name__)


VISIT_EXPR = '''
^                               # Start
\s*                             # Leading whitespace
(i|I|\d)+                       # Numbers as clinic
(\s|\*|\.)+                     # Whitespace or '*' or '.'
((1|i|I)|((i|I|o|O|[0-9])+))    # Either 1 or numbers as mobile
(\s|\*|\.)+                     # Whitespace or '*' or '.'
(i|I|o|O|[0-9])+                # Numbers as serial
(\s|\*|\.)+                     # Whitespace or '*' or '.'
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

    serial_min = 1
    serial_max = 6
    min_wait_time = 1800  # Minimum time between visits by same patient in seconds

    def replace_alpha(self, text):
        """Convert 'o' and 'O' to '0', and 'i', 'I' to '1'."""
        return text.replace('o', '0').replace('O', '0').replace('i', '1').replace(
            'I', '1').replace('*', ' ').replace('.', ' ')

    def clean_text(self):
        """Validate input text.

        text is in format: CLINIC MOBILE SERIAL SERVICE
        """
        error_list = []
        # How come this is available here?
        sender = self.cleaned_data['phone']

        cleaned_data = self.replace_alpha(self.cleaned_data['text'].strip())
        clnc, mobile, serial, srvc = cleaned_data.split()
        logger.debug("text from {0} is {1}".format(sender, cleaned_data))

        # Check if mobile is correct
        if len(mobile) not in [1, 11]:
            error_list.append('mobile')
            logger.debug("Wrong mobile entered: {}".format(mobile))

        # Check if clinic is valid
        try:
            clinic = models.Clinic.objects.get(code=clnc)
        except (models.Clinic.DoesNotExist, ValueError):
            error_list.append('clinic')
            clinic = None

        # Check if serial is valid
        if len(serial) < self.serial_min or len(serial) > self.serial_max:
            error_list.append('serial')
            logger.debug("Wrong serial entered: {}".format(serial))

        # Check if Service is valid
        try:
            service = models.Service.objects.get(code=srvc)
        except models.Service.DoesNotExist:
            error_list.append('service')
            service = None

        # Check if there are errors.
        # If 2 previous validation errors exist, allow entry to pass
        # As long as mobile is ok.
        if len(error_list) > 0:
            fld_list = ', '.join(error_list).upper()
            logger.debug("The errors in error_list are {}".format(fld_list))
            if models.VisitRegistrationError.objects.filter(
                    sender=sender).count() >= 2 and 'mobile' not in error_list:
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
                error_msg = 'Error for serial {0}. There was a mistake in entering '\
                    '{1}. Please check and enter the whole registration '\
                    'code again.'.format(serial, fld_list)
                raise forms.ValidationError(error_msg)
        else:
            # Clear Current Error state
            models.VisitRegistrationError.objects.filter(
                sender=sender).delete()
            # Check if a duplicate in 30 mins
            min_wait_time = timezone.now() - timedelta(
                seconds=self.min_wait_time)
            if models.Visit.objects.filter(
                    mobile=mobile,
                    patient__serial=serial,
                    patient__clinic=clinic,
                    visit_time__gt=min_wait_time).count():
                raise forms.ValidationError("Registration for patient with serial {} was"
                                            " received before. Thank you.".format(serial))

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

    def clean_phone(self):
        """Validate that phone is not in blocked list."""
        blocked = models.Visit.objects.exclude(sender='').values_list('sender', flat=True)
        phone = survey_utils.convert_to_local_format(self.cleaned_data['phone'])
        if phone in blocked:
            raise forms.ValidationError('The phone is not allowed')
        return self.cleaned_data['phone']

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
