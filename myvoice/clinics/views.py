from itertools import groupby
import json
from operator import attrgetter, itemgetter
from datetime import timedelta

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView
from django.utils import timezone
from django.db.models.aggregates import Max, Min

from myvoice.core.utils import get_week_start, get_week_end, make_percentage, get_date
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


class ReportMixin(object):

    def _check_assumptions(self):
        """Fail fast if our hard-coded assumpions are not met."""
        for label in ['Open Facility', 'Respectful Staff Treatment',
                      'Clean Hospital Materials', 'Charged Fairly',
                      'Wait Time']:
            if label not in self.questions:
                raise Exception("Expecting question with label " + label)

    def initialize_data(self, obj):
        """Called by get_object to initialize state information."""
        self.survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
        self.questions = self.survey.surveyquestion_set.all()
        self.questions = dict([(q.label, q) for q in self.questions])
        self._check_assumptions()

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
                    answers = [response.response for response in question_responses]
                    percentage = survey_utils.analyze(answers, question.primary_answer)
                    service_data.append([label.replace(" ", "_"),
                                        '{}%'.format(percentage), total_responses])
                else:
                    service_data.append([None, 0])
            if 'Wait Time' in responses_by_question:
                wait_times = [r.response for r in responses_by_question['Wait Time']]
                mode = survey_utils.get_mode(wait_times)
                service_data.append(["Wait_Time", mode, len(wait_times)])
            else:
                service_data.append([None, None, 0])
            data.append((service, service_data))
        return data


class ClinicReport(ReportMixin, DetailView):
    template_name = 'clinics/report.html'
    model = models.Clinic

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
        self.initialize_data(obj)
        self.responses = obj.surveyquestionresponse_set.all()
        self.responses = self.responses.select_related('question', 'service', 'visit')
        self.generic_feedback = obj.genericfeedback_set.all()
        return obj

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
                    answers = [response.response for response in question_responses]
                    percentage = survey_utils.analyze(answers, question.primary_answer)
                    week_data.append((percentage, total_responses))
                else:
                    week_data.append((None, 0))
            wait_times = [r.response for r in responses_by_question.get('Wait Time', [])]
            data.append({
                'week_start': week_start,
                'week_end': get_week_end(week_start),
                'data': week_data,
                'patient_satisfaction': self._get_patient_satisfaction(week_responses),
                'wait_time_mode': survey_utils.get_mode(wait_times)
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


class RegionReport(ReportMixin, DetailView):
    template_name = 'clinics/summary.html'
    model = models.Region

    def __init__(self, *args, **kwargs):
        super(RegionReport, self).__init__(*args, **kwargs)
        self.curr_date = None
        self.start_date = None
        self.end_date = None
        self.weeks = None

    def get(self, request, *args, **kwargs):
        if 'day' in request.GET and 'month' in request.GET and 'year' in request.GET:
            day = request.GET.get('day')
            month = request.GET.get('month')
            year = request.GET.get('year')
            try:
                self.curr_date = timezone.now().replace(
                    year=int(year), month=int(month), day=int(day))
            except (TypeError, ValueError):
                pass
        return super(RegionReport, self).get(request, *args, **kwargs)

    def calculate_date_range(self):
        try:
            self.start_date = get_week_start(self.curr_date)
            self.end_date = get_week_end(self.curr_date)
        except (ValueError, AttributeError):
            pass

    def calculate_weeks_ranges(self):
        """Returns a list of tuples of dates between self.start_date and self.end_date"""
        week_list = [{"start": self.start_date, "end": self.end_date}]
        start_date = get_week_start(self.start_date)

        next_monday = self.start_date
        while(next_monday < self.end_date):
            next_monday = start_date + timedelta(days=0, weeks=1)
            week_list.append({"start": start_date, "end": next_monday})
            start_date = next_monday
        self.weeks = week_list

    def get_object(self, queryset=None):
        obj = super(RegionReport, self).get_object(queryset)
        self.calculate_date_range()
        self.initialize_data(obj)
        self.responses = SurveyQuestionResponse.objects.filter(clinic__lga__iexact=obj.name)
        if self.start_date and self.end_date:
            self.responses = self.responses.filter(
                visit__visit_time__range=(self.start_date, self.end_date))
        else:
            self.start_date = self.responses.aggregate(min_date=Min('datetime'))['min_date']
            self.end_date = self.responses.aggregate(max_date=Max('datetime'))['max_date']
        self.calculate_weeks_ranges()
        self.responses = self.responses.select_related('question', 'service', 'visit')
        return obj

    def get_context_data(self, **kwargs):
        kwargs['responses'] = self.responses
        kwargs['feedback_by_service'] = self.get_feedback_by_service()
        kwargs['feedback_by_clinic'] = self.get_feedback_by_clinic()
        kwargs['min_date'] = self.start_date
        kwargs['max_date'] = self.end_date
        kwargs['weeks'] = self.weeks
        data = super(RegionReport, self).get_context_data(**kwargs)
        return data

    def get_satisfaction_counts(self, responses):
        """Return satisfaction percentage and total of survey participants

        responses is already grouped by question."""
        if not responses:
            return 0, 0
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

    def get_feedback_participation(self, responses, clinic):
        """Return % of surveys responded to to total visits.

        responses already grouped by question."""
        survey_count = len(responses.get('Open Facility', []))
        visits = models.Visit.objects.filter(
            patient__clinic=clinic, survey_sent__isnull=False)
        if self.curr_date:
            visits = visits.filter(visit_time__range=(self.start_date, self.end_date))
        total_visits = visits.count()

        if total_visits:
            survey_percent = make_percentage(survey_count, total_visits)
        else:
            survey_percent = None
        return survey_percent, total_visits

    def get_feedback_by_clinic(self):
        """Return analyzed feedback by clinic then question."""
        data = []

        # So we can get the name of the clinic for the template
        clinic_map = dict(models.Clinic.objects.values_list('id', 'name'))

        responses = self.responses.exclude(clinic=None)

        print self.start_date
        print self.end_date

        if self.start_date and self.end_date:
            responses = responses.filter(visit__visit_time__range=(self.start_date, self.end_date))

        responses = responses.values(
            'clinic', 'question__label', 'response')

        by_clinic = survey_utils.group_responses(responses, 'clinic', keyfunc=itemgetter)

        # Add clinics without responses back.
        clinic_ids = [clinic[0] for clinic in by_clinic]
        rest_clinics = set(clinic_map.keys()).difference(clinic_ids)

        for _clinic in rest_clinics:
            by_clinic.append((_clinic, []))

        for clinic, clinic_responses in by_clinic:
            by_question = survey_utils.group_responses(
                clinic_responses, 'question__label', keyfunc=itemgetter)
            responses_by_question = dict(by_question)

            # Get feedback participation
            survey_percent, total_visits = self.get_feedback_participation(
                responses_by_question, clinic)

            # Get patient satisfaction
            satis_percent, satis_total = self.get_satisfaction_counts(responses_by_question)

            # Build the data
            clinic_data = [
                ("Participation", '{}%'.format(survey_percent), total_visits),
                ("Patient_Satisfaction", '{}%'.format(satis_percent), satis_total),
                ("Quality", None, 0),
                ("Quantity", None, 0)
            ]
            for label in ['Open Facility', 'Respectful Staff Treatment',
                          'Clean Hospital Materials', 'Charged Fairly']:
                if label in responses_by_question:
                    question = self.questions[label]
                    question_responses = responses_by_question[label]
                    total_responses = len(question_responses)
                    answers = [response['response'] for response in question_responses]
                    percentage = survey_utils.analyze(answers, question.primary_answer)
                    clinic_data.append((label.replace(" ", "_"),
                                        '{}%'.format(percentage), total_responses))
                else:
                    clinic_data.append((None, None, 0))

            if 'Wait Time' in responses_by_question:
                wait_times = [r['response'] for r in responses_by_question['Wait Time']]
                mode = survey_utils.get_mode(wait_times)
                clinic_data.append(("Wait_Time", mode, len(wait_times)))
            else:
                clinic_data.append((None, 0))
            data.append((clinic, clinic_map[clinic], clinic_data))
        return data


class LGAReportFilterByService(View):

    def get_variable(self, request, variable_name, ignore_value):
        if request.GET.get(variable_name):
            the_variable_data = request.GET[variable_name]
            if str(the_variable_data) is str(ignore_value):
                the_variable_data = ""
        else:
            the_variable_data = ""
        return the_variable_data

    def get(self, request):

        # Get the variables
        the_start_date = get_date(self.get_variable(request, "start_date", "Start Date"))
        the_end_date = get_date(self.get_variable(request, "end_date", "End Date"))

        r = ReportMixin()
        r.initialize_data("")
        r.responses = SurveyQuestionResponse.objects.filter(
            visit__visit_time__range=(the_start_date, the_end_date))
        results = []
        content = r.get_feedback_by_service()

        # Convert the Service Objects to only names, plus id's for ajax
        for obj in content:

            new_obj = []
            counter = 0
            for data in obj[1]:
                try:
                    new_obj.append([data[0], data[1], data[2]])
                except:
                    pass
                counter += 1

            obj = [obj[0].id, obj[0].name, new_obj]
            results.append(obj)

        return HttpResponse(json.dumps(results), content_type="text/json")


class LGAReportFilterByClinic(View):

    def get_variable(self, request, variable_name, ignore_value):
        if request.GET.get(variable_name):
            the_variable_data = request.GET[variable_name]
            if str(the_variable_data) is str(ignore_value):
                the_variable_data = ""
        else:
            the_variable_data = ""
        return the_variable_data

    def get(self, request):

        # Get the variables
        the_start_date = self.get_variable(request, "start_date", "Start Date")
        the_end_date = self.get_variable(request, "end_date", "End Date")

        r = RegionReport()                  # Create an instance of Report

        r.start_date = get_date(the_start_date)
        r.end_date = get_date(the_end_date)
        r.curr_date = r.end_date

        r.calculate_date_range()
        r.initialize_data("")
        r.responses = SurveyQuestionResponse.objects.all()

        content = r.get_feedback_by_clinic()

        return HttpResponse(json.dumps(content), content_type="text/json")


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
