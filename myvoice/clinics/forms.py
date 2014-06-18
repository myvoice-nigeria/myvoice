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
