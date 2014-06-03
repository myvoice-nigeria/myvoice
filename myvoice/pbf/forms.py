from django import forms



class SelectClinicForm(forms.Form):
    clinic = forms.ChoiceField(choices=[])

    def __init__(self, *args, **kwargs):
        super(SelectClinicForm, self).__init__(*args, **kwargs)
        from .models import CLINIC_DATA
        choices = [(slug, data['name']) for slug, data in CLINIC_DATA.items()]
        choices.sort(key=lambda c: c[1])
        self.fields['clinic'].choices = choices
