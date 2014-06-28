from django.http import HttpResponse
from django.views.generic import View

import json

from myvoice.clinics import forms
from myvoice.clinics import models


class VisitView(View):
    form_class = forms.VisitForm
    success_msg = "Thank you for registering"
    error_msg = "Your message is invalid, please retry"

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            clnc, phone, srl, serv = form.cleaned_data['text']
            try:
                patient = models.Patient.objects.get(clinic=clnc, serial=srl)
            except models.Patient.DoesNotExist:
                patient = models.Patient.objects.create(
                    clinic=clnc,
                    serial=srl,
                    mobile=phone)

            models.Visit.objects.create(patient=patient, service=serv)
            return HttpResponse(json.dumps({'text': self.success_msg}))
        else:
            return HttpResponse(json.dumps({'text': self.get_error_msg(form)}))

    def get_error_msg(self, form):
        """Extract the first error message from the form's 'text' field."""
        return form.errors['text'][0]
