from django.http import HttpResponse, HttpResponseBadRequest

import json

from myvoice.clinics import forms
from myvoice.clinics import models


ERROR_MSG = 'Your message is invalid, please retry'
SUCCESS_MSG = 'Thank you for registering'


def visit(request):
    if request.method == 'POST':
        form = forms.VisitForm(request.POST)
        if form.is_valid():
            clnc, phone, serial, service = form.cleaned_data['text']
            #TODO: Validate that serial is not diff for same clinic
            # and update phone number if it is the default
            patient, _ = models.Patient.objects.get_or_create(
                clinic=clnc, serial=serial)
            models.Visit.objects.create(
                patient=patient,
                service=service)
            response = json.dumps({'text': SUCCESS_MSG})
        else:
            response = json.dumps({'text': ERROR_MSG})
        return HttpResponse(response)
    else:
        return HttpResponseBadRequest('Only POST allowed')
    return HttpResponse('')
