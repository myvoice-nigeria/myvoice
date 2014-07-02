from collections import Counter, defaultdict
from itertools import groupby
import json
import operator

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView
from django.shortcuts import redirect

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

    def _analyze(self, responses, answer):
        """Return the percentage of responses with the specified answer."""
        if not responses:
            return None  # Avoid divide-by-0 error.
        count = len([r for r in responses if r.response == answer])
        return round(float(count) / len(responses) * 100, 2)

    def _check_assumptions(self):
        """Fail fast if our hard-coded assumpions are not met."""
        for label in ['Open Facility', 'Respectful Staff Treatment',
                      'Clean Hospital Materials', 'Charged Fairly',
                      'Wait Time']:
            if label not in self.questions:
                raise Exception("Expecting question with label " + label)

    def _get_mode(self, answers):
        """Return the most commonly reported answer."""
        if answers:
            return max(Counter(answers).iteritems(), key=operator.itemgetter(1))[0]
        return None

    def get_object(self, queryset=None):
        obj = super(ClinicReport, self).get_object(queryset)
        self.survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
        self.questions = self.survey.surveyquestion_set.all()
        self.questions = dict([(q.label, q) for q in self.questions])
        self.responses = obj.surveyquestionresponse_set.all()
        self.responses = self.responses.select_related('question', 'service')
        self._check_assumptions()
        return obj

    def get_detailed_comments(self):
        """
        Return all open-ended responses. Ordered by question, so that we can
        use {% regroup %} in the template.
        """
        comments = self.responses.filter(
            question__question_type=SurveyQuestion.OPEN_ENDED)
        comments = comments.order_by('question')
        return comments

    def get_feedback_by_service(self):
        """Return analyzed feedback by service then question."""
        data = []
        responses = self.responses.order_by('service')
        for service, service_responses in groupby(responses, lambda r: r.service):
            responses_by_question = defaultdict(list)
            for response in service_responses:
                responses_by_question[response.question.label].append(response)

            service_data = []
            for label in ['Open Facility', 'Respectful Staff Treatment',
                          'Clean Hospital Materials', 'Charged Fairly']:
                if label in responses_by_question:
                    question = self.questions[label]
                    question_responses = responses_by_question[label]
                    total_responses = len(question_responses)
                    percentage = self._analyze(question_responses, question.get_categories()[0])
                    service_data.append(('{}%'.format(percentage), total_responses))
                else:
                    service_data.append((None, 0))
            if 'Wait Time' in responses_by_question:
                wait_times = [r.response for r in responses_by_question['Wait Time']]
                mode = self._get_mode(wait_times)
                service_data.append((mode, len(wait_times)))
            else:
                service_data.append((None, 0))
            data.append((service, service_data))
        return data

    def get_context_data(self, **kwargs):
        kwargs['detailed_comments'] = self.get_detailed_comments()
        kwargs['feedback_by_service'] = self.get_feedback_by_service()
        return super(ClinicReport, self).get_context_data(**kwargs)
