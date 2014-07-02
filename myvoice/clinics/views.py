from collections import Counter
import json
import operator

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView
from django.shortcuts import redirect

from myvoice.clinics.models import Service
from myvoice.survey.models import SurveyQuestion, Survey

from . import forms
from . import models


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


class ClinicReportSelectClinic(FormView):
    template_name = 'clinics/select.html'
    form_class = forms.SelectClinicForm

    def form_valid(self, form):
        clinic = form.cleaned_data['clinic']
        return redirect('clinic_report', slug=clinic.slug)


class ClinicReport(DetailView):
    template_name = 'clinics/report.html'
    model = models.Clinic

    def get_object(self, queryset=None):
        obj = super(ClinicReport, self).get_object(queryset)

        self.survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
        self.questions = self.survey.surveyquestion_set.all()
        self.questions = dict([(q.label, q) for q in self.questions])

        self.responses = obj.surveyquestionresponse_set.all().select_related('question')

        self.services = Service.objects.filter(
            surveyquestionresponse__in=self.responses).distinct()

        self.responses_by_question = {}
        for label in ['Open Facility', 'Respectful Staff Treatment',
                      'Clean Hospital Materials', 'Charged Fairly',
                      'Wait Time']:
            if label not in self.questions:
                # Fail fast if our hard-coded expectations aren't met.
                raise Exception("Expecting question with label " + label)
            responses = self.responses.filter(question=self.questions.get(label))
            self.responses_by_question[label] = responses

        return obj

    def get_detailed_comments(self):
        """Return all open-ended responses.

        Ordered by question label, so that we can use {% regroup %}.
        """
        comments = self.responses.filter(question__question_type=SurveyQuestion.OPEN_ENDED)
        comments = comments.select_related('question', 'connection')
        comments = comments.order_by('question__label')
        return comments

    def get_feedback_analytics(self, responses=None):
        if responses is None:
            responses = self.responses
        data = []
        for label in ['Open Facility', 'Respectful Staff Treatment',
                      'Clean Hospital Materials', 'Charged Fairly']:
            question = self.questions.get(label)
            main_choice = question.get_categories()[0]
            question_responses = self.responses_by_question.get(label)
            main_choice_count = question_responses.filter(response=main_choice).count()
            if question_responses:
                percentage = round(float(main_choice_count) / len(question_responses) * 100, 2)
            else:
                percentage = 0
            data.append((question, percentage, len(question_responses)))
        return data

    def get_feedback_by_service(self):
        data = []
        for service in self.services:
            responses = self.responses.filter(service=service)
            data.append((service, self.get_feedback_analytics(responses),
                         self.get_most_common_wait_time(responses)))
        return data

    def get_most_common_wait_time(self, responses=None):
        """Return the most commonly reported wait time."""
        if responses is None:
            responses = self.responses
        wait_times = responses.filter(question__label='Wait Time')
        wait_times = wait_times.values_list('response', flat=True)
        if wait_times:
            return max(Counter(wait_times).iteritems(), key=operator.itemgetter(1))[0]
        return None

    def get_patient_satisfaction(self):
        pass  # TODO

    def get_context_data(self, **kwargs):
        kwargs['detailed_comments'] = self.get_detailed_comments()
        kwargs['feedback_analytics'] = self.get_feedback_analytics()
        kwargs['feedback_by_service'] = self.get_feedback_by_service()
        kwargs['most_common_wait_time'] = self.get_most_common_wait_time()
        kwargs['patient_satisfaction'] = self.get_patient_satisfaction()
        return super(ClinicReport, self).get_context_data(**kwargs)
