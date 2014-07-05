from itertools import groupby
import json
from operator import attrgetter

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView

from myvoice.clinics.models import Visit
from myvoice.core.utils import get_week_start, get_week_end
from myvoice.survey import utils as survey_utils
from myvoice.survey.models import SurveyQuestion, Survey

from . import forms
from . import models


class VisitView(View):
    form_class = forms.VisitForm
    success_msg = "Entry was received. Thank you."
    error_msg = "Your message is invalid, please retry"
    serial_min = 3
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

    def _check_assumptions(self):
        """Fail fast if our hard-coded assumpions are not met."""
        for label in ['Open Facility', 'Respectful Staff Treatment',
                      'Clean Hospital Materials', 'Charged Fairly',
                      'Wait Time']:
            if label not in self.questions:
                raise Exception("Expecting question with label " + label)

    def _get_patient_satisfaction(self, responses):
        """Patient satisfaction is gauged on their answers to 3 questions."""
        if not responses:
            return None  # Avoid divide-by-zero error.
        grouped = groupby(sorted(responses, key=attrgetter('phone')), lambda r: r.phone)
        grouped = [(l, dict([(rr.question.label, rr.response) for rr in r]))
                   for l, r in grouped]
        treatment = self.questions['Respectful Staff Treatment']
        overcharge = self.questions['Charged Fairly']
        wait_time = self.questions['Wait Time']
        unsatisfied_count = 0
        for phone, answers in grouped:
            if treatment.label in answers:
                if answers.get(treatment.label) != treatment.primary_answer:
                    unsatisfied_count += 1
                    continue
            if overcharge.label in answers:
                if answers.get(overcharge.label) != overcharge.primary_answer:
                    unsatisfied_count += 1
                    continue
            if wait_time.label in answers:
                if answers.get(wait_time.label) == wait_time.get_categories()[-1]:
                    unsatisfied_count += 1
                    continue
        return 100 - int(float(unsatisfied_count) / len(grouped) * 100)

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
        comments = comments.order_by('question', 'datetime')
        return comments

    def get_feedback_by_service(self):
        """Return analyzed feedback by service then question."""
        data = []
        responses = self.responses.order_by('service', 'question')
        for service, service_responses in groupby(responses, lambda r: r.service):
            responses_by_question = survey_utils.group_by_question(service_responses)
            service_data = []
            for label in ['Open Facility', 'Respectful Staff Treatment',
                          'Clean Hospital Materials', 'Charged Fairly']:
                if label in responses_by_question:
                    question = self.questions[label]
                    question_responses = responses_by_question[label]
                    total_responses = len(question_responses)
                    percentage = survey_utils.analyze(question_responses, question.primary_answer)
                    service_data.append(('{}%'.format(percentage), total_responses))
                else:
                    service_data.append((None, 0))
            if 'Wait Time' in responses_by_question:
                wait_times = responses_by_question['Wait Time']
                mode = survey_utils.get_mode(wait_times)
                service_data.append((mode, len(wait_times)))
            else:
                service_data.append((None, 0))
            data.append((service, service_data))
        return data

    def get_feedback_by_week(self):
        responses = self.responses.order_by('datetime', 'question__label')
        data = []
        for week_start, week_responses in groupby(responses, lambda r: get_week_start(r.datetime)):
            week_responses = list(week_responses)
            responses_by_question = survey_utils.group_by_question(week_responses)
            week_data = []
            for label in ['Open Facility', 'Respectful Staff Treatment',
                          'Clean Hospital Materials', 'Charged Fairly']:
                if label in responses_by_question:
                    question = self.questions[label]
                    question_responses = list(responses_by_question[label])
                    total_responses = len(question_responses)
                    percentage = survey_utils.analyze(question_responses, question.primary_answer)
                    week_data.append((percentage, total_responses))
                else:
                    week_data.append((None, 0))
            data.append({
                'week_start': week_start,
                'week_end': get_week_end(week_start),
                'data': week_data,
                'patient_satisfaction': self._get_patient_satisfaction(week_responses),
                'wait_time_mode': survey_utils.get_mode(responses_by_question['Wait Time']),
            })
        return data

    def get_date_range(self):
        if self.responses:
            min_date = min(self.responses, key=attrgetter('datetime')).datetime
            max_date = max(self.responses, key=attrgetter('datetime')).datetime
            return get_week_start(min_date), get_week_end(max_date)
        return None, None

    def get_num_registered(self):
        """Return the number patients that should have received this survey."""
        return Visit.objects.filter(patient__clinic=self.object).count()

    def get_num_completed(self):
        """Return the number of surveys which have been completed."""
        labels = ['Open Facility', 'Respectful Staff Treatment',
                  'Clean Hospital Materials', 'Charged Fairly',
                  'Wait Time']
        results = groupby(self.responses, attrgetter('phone'))
        results = [[r.question.label for r in list(i[1])] for i in results]
        return len([r for r in results if all([l in r for l in labels])])

    def get_context_data(self, **kwargs):
        kwargs['responses'] = self.responses
        kwargs['detailed_comments'] = self.get_detailed_comments()
        kwargs['feedback_by_service'] = self.get_feedback_by_service()
        kwargs['feedback_by_week'] = self.get_feedback_by_week()
        kwargs['min_date'], kwargs['max_date'] = self.get_date_range()
        kwargs['num_registered'] = self.get_num_registered()
        kwargs['num_completed'] = self.get_num_completed()
        # TODO - participation rank amongst other clinics.
        return super(ClinicReport, self).get_context_data(**kwargs)


class RegionReport(DetailView):
    template_name = 'clinics/summary.html'
    model = models.Region


class FeedbackView(View):
    form_class = forms.FeedbackForm

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(FeedbackView, self).dispatch(*args, **kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            values = form.cleaned_data['values']
            models.GenericFeedback.objects.create(
                sender=form.cleaned_data['phone'],
                clinic=values.get('clinic'),
                message=values.get('message'))

        return HttpResponse('ok')
