from django import forms

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
    phone = forms.CharField(max_length=20, required=False)
    text = forms.RegexField('^\d{1,3}\s+((1)|(0[789]\d{9}))\s+\d{4,6}\s+\d+$', max_length=50)

    def clean_text(self):
        """Validate input text.

        text is in format: CLINIC PHONE SERIAL SERVICE
        """
        #srvc = self.cleaned_data['text'].split()
        clnc, phone, serial, srvc = self.cleaned_data['text'].split()
        #import pdb;pdb.set_trace()
        # Check if clinic is valid
        try:
            clinic = models.Clinic.objects.get(code=clnc)
        except (models.Clinic.DoesNotExist, ValueError):
            raise forms.ValidationError('Invalid clinic code')

        # Check if service is valid
        try:
            service = models.Service.objects.get(code=srvc)
        except (models.Service.DoesNotExist, ValueError):
            raise forms.ValidationError('Invalid service code')

        return clinic, phone, serial, service
