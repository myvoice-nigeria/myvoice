from django.http import HttpResponse
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt

import json

from myvoice.clinics import forms
from myvoice.clinics import models


class VisitView(View):
    form_class = forms.VisitForm
    success_msg = "Entry was received. Thank you."
    error_msg = "Your message is invalid, please retry"
    serial_min = 4
    serial_max = 6

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(VisitView, self).dispatch(*args, **kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            # Serial and Service are not validated in the form.
            clnc, mobile, serial, serv, txt = form.cleaned_data['text']
            phone = form.cleaned_data['phone']
            try:
                patient = models.Patient.objects.get(clinic=clnc, serial=serial)
            except models.Patient.DoesNotExist:
                patient = models.Patient.objects.create(
                    clinic=clnc,
                    serial=serial,
                    mobile=mobile)

            output_msg = self.success_msg

            # Check if Serial is correct, not a show-stopper.
            if len(serial) < self.serial_min or len(serial) > self.serial_max:
                output_msg = 'Serial number does not seem correct, but patient was registered. '\
                             'Thank you.'
                models.VisitRegistrationErrorLog.objects.create(
                    sender=phone, error_type='Wrong Serial', message=txt)

            # Check if Service is correct, not a show-stopper
            try:
                serv = models.Service.objects.get(code=serv)
            except models.Service.DoesNotExist:
                serv = None
                output_msg = 'Service code does not seem correct, but patient was registered. '\
                             'Thank you.'
                models.VisitRegistrationErrorLog.objects.create(
                    sender=phone, error_type='Wrong Service Code', message=txt)

            # Check if Clinic is None
            if not clnc:
                output_msg = 'Clinic code does not seem correct, but patient was registered. '\
                             'Thank you.'

            models.Visit.objects.create(patient=patient, service=serv)
            data = json.dumps({'text': output_msg})
        else:
            data = json.dumps({'text': self.get_error_msg(form)})

        response = HttpResponse(data, mimetype='text/json')

        # This is to test webhooks from localhost
        # response['Access-Control-Allow-Origin'] = '*'
        return response

    def get_error_msg(self, form):
        """Extract the first error message from the form's 'text' field."""
        return form.errors['text'][0]


class FeedbackView(View):
    form_class = forms.FeedbackForm

    def post(self, request):
        form = self.form_class(request.POST)
        #import pdb;pdb.set_trace()
        if form.is_valid():
            sender = form.cleaned_data['phone']
            data = form.cleaned_data['values']

            return HttpResponse('ok')
