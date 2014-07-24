from itertools import groupby
import json
from operator import attrgetter

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView
from django.utils import timezone

from myvoice.core.utils import get_week_start, get_week_end, make_percentage
from myvoice.survey import utils as survey_utils
from myvoice.survey.models import Survey, SurveyQuestion, SurveyQuestionResponse

from . import forms
from . import models


class VisitView(View):
    form_class = forms.VisitForm
    success_msg = "Entry received for patient with serial number {}. Thank you."
    error_msg = "1 or more of your entry are missing, please check and enter "\
                "the registration agian."
    serial_min = 3
    serial_max = 6

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(VisitView, self).dispatch(*args, **kwargs)

    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():

            clnc, mobile, serial, serv, txt = form.cleaned_data['text']
            try:
                patient = models.Patient.objects.get(clinic=clnc, serial=serial)
            except models.Patient.DoesNotExist:
                patient = models.Patient.objects.create(
                    clinic=clnc,
                    serial=serial,
                    mobile=mobile)

            output_msg = self.success_msg.format(serial)

            models.Visit.objects.create(patient=patient, service=serv, mobile=mobile)
            data = json.dumps({'text': output_msg})
        else:
            data = json.dumps({'text': self.get_error_msg(form)})

        response = HttpResponse(data, content_type='text/json')

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
        treatment = self.questions['Respectful Staff Treatment']
        overcharge = self.questions['Charged Fairly']
        wait_time = self.questions['Wait Time']
        unsatisfied_count = 0
        grouped = survey_utils.group_responses(responses, 'visit.id', 'visit')
        required = ['Respectful Staff Treatment', 'Clean Hospital Materials',
                    'Charged Fairly', 'Wait Time']
        count = 0  # Number of runs that contain at least one required question.
        for visit, visit_responses in grouped:
            # Map question label to the response given for that question.
            answers = dict([(r.question.label, r.response) for r in visit_responses])
            if any([r in answers for r in required]):
                count += 1
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
        if not count:
            return None
        return 100 - make_percentage(unsatisfied_count, count)

    def get_object(self, queryset=None):
        obj = super(ClinicReport, self).get_object(queryset)
        self.survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
        self.questions = self.survey.surveyquestion_set.all()
        self.questions = dict([(q.label, q) for q in self.questions])
        self.responses = obj.surveyquestionresponse_set.all()
        self.responses = self.responses.select_related('question', 'service', 'visit')
        self.generic_feedback = obj.genericfeedback_set.all()
        self._check_assumptions()
        return obj

    def get_feedback_by_service(self):
        """Return analyzed feedback by service then question."""
        data = []
        responses = self.responses.exclude(service=None)
        by_service = survey_utils.group_responses(responses, 'service.id', 'service')
        for service, service_responses in by_service:
            by_question = survey_utils.group_responses(service_responses, 'question.label')
            responses_by_question = dict(by_question)
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
        data = []
        responses = self.responses.order_by('datetime')
        by_week = groupby(responses, lambda r: get_week_start(r.datetime))
        for week_start, week_responses in by_week:
            week_responses = list(week_responses)
            by_question = survey_utils.group_responses(week_responses, 'question.label')
            responses_by_question = dict(by_question)
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
                'wait_time_mode': survey_utils.get_mode(responses_by_question.get('Wait Time', [])),
            })
        return data

    def get_date_range(self):
        if self.responses:
            min_date = min(self.responses, key=attrgetter('datetime')).datetime
            max_date = max(self.responses, key=attrgetter('datetime')).datetime
            return get_week_start(min_date), get_week_end(max_date)
        return None, None

    def get_detailed_comments(self):
        """Combine open-ended survey comments with General Feedback."""
        open_ended_responses = self.responses.filter(
            question__question_type=SurveyQuestion.OPEN_ENDED,
            display_on_dashboard=True)
        comments = [
            {
                'question': r.question.label,
                'datetime': r.datetime,
                'response': r.response,
            }
            for r in open_ended_responses
            if survey_utils.display_feedback(r.response)
        ]

        feedback_label = self.generic_feedback.model._meta.verbose_name
        for feedback in self.generic_feedback:
            if survey_utils.display_feedback(feedback.message):
                comments.append(
                    {
                        'question': feedback_label,
                        'datetime': feedback.message_date,
                        'response': feedback.message
                    })

        return sorted(comments, key=lambda item: (item['question'], item['datetime']))

    def get_context_data(self, **kwargs):
        kwargs['responses'] = self.responses
        kwargs['detailed_comments'] = self.get_detailed_comments()
        kwargs['feedback_by_service'] = self.get_feedback_by_service()
        kwargs['feedback_by_week'] = self.get_feedback_by_week()
        kwargs['min_date'], kwargs['max_date'] = self.get_date_range()
        num_registered = survey_utils.get_registration_count(self.object)
        num_started = survey_utils.get_started_count(self.responses)
        num_completed = survey_utils.get_completion_count(self.responses)

        if num_registered:
            percent_started = make_percentage(num_started, num_registered)
            percent_completed = make_percentage(num_completed, num_registered)
        else:
            percent_completed = None
            percent_started = None

        kwargs['num_registered'] = num_registered
        kwargs['num_started'] = num_started
        kwargs['percent_started'] = percent_started
        kwargs['num_completed'] = num_completed
        kwargs['percent_completed'] = percent_completed

        # TODO - participation rank amongst other clinics.
        return super(ClinicReport, self).get_context_data(**kwargs)


class RegionReport(ClinicReport):
    template_name = 'clinics/lgasummary.html'
    model = models.Region

    def get(self, request, *args, **kwargs):
        if 'day' in request.GET and 'month' in request.GET and 'year' in request.GET:
            day = request.GET.get('day')
            month = request.GET.get('month')
            year = request.GET.get('year')
            try:
                self.curr_date = timezone.datetime(int(year), int(month), int(day))
            except:
                self.curr_date = timezone.datetime.now()
        else:
            self.curr_date = timezone.datetime.now()
        self.calculate_date_range()
        return super(RegionReport, self).get(request, *args, **kwargs)

    def calculate_date_range(self):
        try:
            self.start_date = get_week_start(self.curr_date)
            self.end_date = get_week_end(self.curr_date)
        except:
            curr_date = timezone.datetime.now()
            self.start_date = get_week_start(curr_date)
            self.end_date = get_week_end(curr_date)

    def get_object(self, queryset=None):
        obj = DetailView.get_object(self, queryset)
        self.calculate_date_range()
        self.survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
        self.questions = self.survey.surveyquestion_set.all()
        self.questions = dict([(q.label, q) for q in self.questions])
        self.responses = SurveyQuestionResponse.objects.filter(
            clinic__lga__iexact=obj.name, visit__visit_time__range=(self.start_date, self.end_date))
        self.responses = self.responses.select_related('question', 'service', 'visit')
        self.generic_feedback = models.GenericFeedback.objects.none()
        self._check_assumptions()
        return obj

    def get_context_data(self, **kwargs):
        kwargs['feedback_by_clinic'] = self.get_feedback_by_clinic()
        data = super(RegionReport, self).get_context_data(**kwargs)
        return data

    def get_satisfaction_counts(self, responses):
        """Return satisfaction percentage and total of survey participants."""
        if not responses:
            return None
        unsatisfied, total = 0, 0

        for question, q_responses in responses.items():
            if question in ['Respectful Staff Treatment', 'Charged Fairly']:
                answer = self.questions[question].primary_answer
                unsatisfied += len([r for r in q_responses if r['response'] != answer])
            elif question == 'Wait Time':
                answer = self.questions[question].get_categories()[-1]
                unsatisfied += len([r for r in q_responses if r['response'] == answer])
            total += len(q_responses)

        return 100 - make_percentage(unsatisfied, total), total

    def get_feedback_by_clinic(self):
        """Return analyzed feedback by clinic then question."""
        data = []
        clinic_map = dict(self.responses.exclude(clinic=None).values_list(
            'clinic__id', 'clinic__name').distinct())

        responses = self.responses.exclude(clinic=None).values(
            'clinic', 'question__label', 'response')
        by_clinic = survey_utils.group_response_dicts(responses, 'clinic')

        for clinic, clinic_responses in by_clinic:
            by_question = survey_utils.group_response_dicts(clinic_responses, 'question__label')
            responses_by_question = dict(by_question)

            # Get feedback participation
            survey_count = len(responses_by_question.get('Open Facility', 0))
            total_visits = models.Visit.objects.filter(
                patient__clinic=clinic, survey_sent__isnull=False,
                visit_time__range=(self.start_date, self.end_date)).count()
            if total_visits:
                survey_percent = make_percentage(survey_count, total_visits)
            else:
                survey_percent = None

            # Get patient satisfaction
            satis_percent, satis_total = self.get_satisfaction_counts(responses_by_question)

            # Build the data
            clinic_data = [
                ('{}%'.format(survey_percent), total_visits),
                ('{}%'.format(satis_percent), satis_total),
                (None, 0),
                (None, 0)
            ]
            for label in ['Open Facility', 'Respectful Staff Treatment',
                          'Clean Hospital Materials', 'Charged Fairly']:
                if label in responses_by_question:
                    question = self.questions[label]
                    question_responses = responses_by_question[label]
                    total_responses = len(question_responses)
                    percentage = survey_utils.analyze_dict(
                        question_responses, question.primary_answer)
                    clinic_data.append(('{}%'.format(percentage), total_responses))
                else:
                    clinic_data.append((None, 0))

            if 'Wait Time' in responses_by_question:
                wait_times = responses_by_question['Wait Time']
                mode = survey_utils.get_mode_dict(wait_times)
                clinic_data.append((mode, len(wait_times)))
            else:
                clinic_data.append((None, 0))
            data.append((clinic_map[clinic], clinic_data))
        return data


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
