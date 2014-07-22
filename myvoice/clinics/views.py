from itertools import groupby
import json
from operator import attrgetter
from dateutil.parser import parse

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView, TemplateView

from myvoice.core.utils import get_week_start, get_week_end, make_percentage, daterange
from myvoice.survey import utils as survey_utils

from myvoice.survey.models import Survey, SurveyQuestion, SurveyQuestionResponse
from myvoice.clinics.models import Clinic, Service, Visit

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
        comments = [
            {
                'question': survey.question.label,
                'datetime': survey.datetime,
                'response': survey.response
            } for survey in self.responses.filter(
                question__question_type=SurveyQuestion.OPEN_ENDED)
            ]

        feedback_label = self.generic_feedback.model._meta.verbose_name
        for feedback in self.generic_feedback:
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
        num_completed = survey_utils.get_completion_count(self.responses)
        if num_registered:
            percent_completed = make_percentage(num_completed, num_registered)
        else:
            percent_completed = None
        kwargs['num_registered'] = num_registered
        kwargs['percent_completed'] = percent_completed
        # TODO - participation rank amongst other clinics.
        return super(ClinicReport, self).get_context_data(**kwargs)


class AnalystSummary(TemplateView):
    template_name = 'analysts/analysts.html'
    allowed_methods = ['get', 'post', 'put', 'delete', 'options']

    def options(self, request, id):
        response = HttpResponse()
        response['allow'] = ','.join([self.allowed_methods])
        return response

    def get_completion_table(self, clinic="", start_date="", end_date="", service=""):
        completion_table = []
        st_total = 0            # Surveys Triggered
        ss_total = 0
        sc_total = 0            # Surveys Completed

        # All Clinics to Loop Through, build our own dict of data
        if not clinic:
            clinics_to_add = Clinic.objects.all().order_by("name")
        else:
            if type(clinic) == str:
                clinics_to_add = Clinic.objects.get(name=clinic)
            else:
                clinics_to_add = clinic

        # Filter for Start Date, End Date and Service
        if start_date:
            if type(start_date) is str:
                start_date = parse(start_date)

        if end_date:
            if type(end_date) is str:
                end_date = parse(end_date)

        if service:
            if type(service) is str:
                service = Service.objects.get(name__iexact=service)

        # Loop through the Clinics, summating the data required.
        for a_clinic in clinics_to_add:

            # Survey Triggered (Sent) Query Statistics
            st_query = Visit.objects.filter(
                survey_sent__isnull=False, patient__clinic=a_clinic)
            if start_date:
                st_query = st_query.filter(visit_time__gte=start_date)

            if end_date:
                st_query = st_query.filter(visit_time__lte=end_date)

            if service:
                st_query = st_query.filter(service__name=service)

            st_count = st_query.count()
            st_total += st_count

            # Survey Started Query Statistics
            ss_count = SurveyQuestionResponse.objects\
                .filter(question__question_type__iexact="open-ended").count()
            ss_total += ss_count

            # Survey Completed Query Statistics
            sc_count = SurveyQuestionResponse.objects.filter(question__label="Wait Time")\
                .filter(clinic=a_clinic).count()
            sc_total += sc_count

            # Survey Percentages
            if st_count:
                ss_st_percent = 100*ss_count/st_count
                sc_st_percent = 100*sc_count/st_count
            else:
                ss_st_percent = "--"
                sc_st_percent = "--"

            completion_table.append({
                "clinic_id": a_clinic.id,
                "clinic_name": a_clinic.name,
                "st_count": st_count,
                "ss_count": ss_count,
                "ss_st_percent": ss_st_percent,
                "sc_count": sc_count,
                "sc_st_percent": sc_st_percent
            })

        if st_total:
            ss_st_percent_total = 100*ss_total/st_total
            sc_st_percent_total = 100*sc_total/st_total
        else:
            ss_st_percent_total = "--"
            sc_st_percent_total = "--"

        completion_table.append({
            "clinic_id": -1,
            "clinic_name": "Total",
            "st_count": st_total,
            "ss_count": ss_total,
            "ss_st_percent": ss_st_percent_total,
            "sc_count": sc_total,
            "sc_st_percent": sc_st_percent_total,
        })

        return completion_table

    # Returns a list of Datetime Days between two dates
    def get_date_range(self, start_date, end_date):
        return_dates = []
        if type(start_date) is str:
            start_date = parse(start_date)
        if type(end_date) is str:
            end_date = parse(end_date)
        for single_date in daterange(start_date, end_date):
            return_dates.append(single_date)
        return return_dates

    def get_surveys_triggered_summary(self):
        """Total number of Surveys Triggered."""
        return Visit.objects.filter(survey_sent__isnull=False)

    def get_surveys_started_summary(self):
        return SurveyQuestionResponse.objects.filter(question__question_type__iexact="open-ended")

    def get_surveys_completed_summary(self):
        """Total number of Surveys Completed."""
        return SurveyQuestionResponse.objects.filter(question__label__iexact="Wait Time")

    def get_context_data(self, **kwargs):

        context = super(AnalystSummary, self).\
            get_context_data(**kwargs)

        context['completion_table'] = self.get_completion_table()
        context['st'] = self.get_surveys_triggered_summary()
        context['st_count'] = context['st'].count()

        context['ss'] = self.get_surveys_started_summary()
        context['ss_count'] = context['ss'].count()

        context['sc'] = self.get_surveys_completed_summary()
        context['sc_count'] = context['sc'].count()

        if context['ss_count']:
            context['ss_st_percent'] = 100*context['ss_count']/context['st_count']
        else:
            context['ss_st_percent'] = "--"

        if context['st_count']:
            context['sc_st_percent'] = 100*context['sc_count']/context['st_count']
        else:
            context['sc_st_percent'] = "--"

        # Needed for to populate the Dropdowns (Selects)
        context['services'] = Service.objects.all()
        first_date = Visit.objects.all().order_by("visit_time")[0].visit_time.date()
        last_date = Visit.objects.all().order_by("-visit_time")[0].visit_time.date()
        context['date_range'] = self.get_date_range(first_date, last_date)
        context['clinics'] = Clinic.objects.all().order_by("name")
        return context

    def get_rates_table(self, service="", clinic="", start_date="", end_date=""):
        rates_table = []

        sqr_query = SurveyQuestionResponse.objects.all()
        if clinic:
            sqr_query = sqr_query.filter(clinic__name__iexact=clinic)
        if service:
            sqr_query = sqr_query.filter(service__name__iexact=service)
        if start_date:
            if type(start_date) is str:
                sqr_query = sqr_query.filter(visit_time__gte=parse(start_date))
        if end_date:
            if type(end_date) is str:
                sqr_query = sqr_query.filter(visit_time__lte=parse(end_date))

        rates_table.append({
            "row_num": "1.1",
            "row_title": "1.1 Hospital Availability",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Open Facility").filter(
                question__question_type__iexact='multiple-choice').count()
            })

        rates_table.append({
            "row_num": "1.2",
            "row_title": "1.2 Hospital Availability Comment",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Open Facility").filter(
                question__question_type__iexact="open-ended").count()
        })

        rates_table.append({
            "row_num": "2.1",
            "row_title": "2.1 Respectful Staff Treatment",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Respectful Staff Treatment").filter(
                question__question_type__iexact='multiple-choice').count()
        })

        rates_table.append({
            "row_num": "2.2",
            "row_title": "2.2 Respectful Staff Treatment Comment",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Respectful Staff Treatment").filter(
                question__question_type__iexact='open-ended').count()
        })

        rates_table.append({
            "row_num": "3.1",
            "row_title": "3.1 Clean Hospital Materials",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Clean Hospital Materials").filter(
                question__question_type__iexact='multiple-choice').count()
        })

        rates_table.append({
            "row_num": "3.2",
            "row_title": "3.2 Clean Hospital Materials Comment",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Clean Hospital Materials").filter(
                question__question_type__iexact='open-ended').count()
        })

        rates_table.append({
            "row_num": "4.1",
            "row_title": "4.1 Charged Fairly",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Charged Fairly").filter(
                question__question_type__iexact='multiple-choice').count()
        })

        rates_table.append({
            "row_num": "4.2",
            "row_title": "4.2 Charged Fairly Comment",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Charged Fairly").filter(
                question__question_type__iexact='open-ended').count()
        })

        rates_table.append({
            "row_num": "5.1",
            "row_title": "5.1 Wait Time",
            "rsp_num": sqr_query.filter(
                question__label__iexact="Wait time").filter(
                question__question_type__iexact='multiple-choice').count()
        })

        rates_table.append({
            "row_num": "6.1",
            "row_title": "6.1  General Feedback",
            "rsp_num": sqr_query.filter(
                question__label__iexact="General Feedback").filter(
                question__question_type__iexact='open-ended').count()
        })

        return rates_table


class CompletionFilter(View):

    def get_variable(self, request, variable_name, ignore_value):
        if request.GET.get(variable_name):
            the_variable_data = request.GET[variable_name]
            if str(the_variable_data) is str(ignore_value):
                the_variable_data = ""
        else:
            the_variable_data = ""
        return the_variable_data

    def get(self, request):
        the_service = self.get_variable(request, "service", "Service")
        the_start_date = self.get_variable(request, "start_date", "Start Date")
        the_end_date = self.get_variable(request, "end_date", "End Date")

        if not the_start_date or "Start Date" in the_start_date:
            the_start_date = Visit.objects.all().order_by("visit_time")[0].visit_time.date()
        else:
            the_start_date = parse(the_start_date)
        if not the_end_date or "End Date" in the_end_date:
            the_end_date = Visit.objects.all().order_by("-visit_time")[0].visit_time.date()
        else:
            the_end_date = parse(the_end_date)

        a = AnalystSummary()
        data = a.get_completion_table(
            start_date=the_start_date, end_date=the_end_date, service=the_service)
        content = {"clinic_data": {}}
        for a_clinic in data:
            content["clinic_data"][a_clinic["clinic_id"]] = {
                "name": a_clinic["clinic_name"],
                "st": a_clinic["st_count"],
                "ss": a_clinic["ss_count"],
                "sc": a_clinic["sc_count"],
                "scp": a_clinic["sc_st_percent"]
            }

        return HttpResponse(json.dumps(content), content_type="text/json")


class FeedbackFilter(View):

    def get_variable(self, request, variable_name, ignore_value):
        if request.GET.get(variable_name):
            the_variable_data = request.GET[variable_name]
            if str(the_variable_data) is str(ignore_value):
                the_variable_data = ""
        else:
            the_variable_data = ""
        return the_variable_data

    def get(self, request):
        the_service = self.get_variable(request, "service", "Service")
        the_clinic = self.get_variable(request, "clinic", "Clinic")
        the_start_date = self.get_variable(request, "start_date", "Start Date")
        the_end_date = self.get_variable(request, "end_date", "End Date")

        if not the_start_date or "Start Date" in the_start_date:
            the_start_date = Visit.objects.all().order_by("visit_time")[0].visit_time.date()
        else:
            the_start_date = parse(the_start_date)
        if not the_end_date or "End Date" in the_end_date:
            the_end_date = Visit.objects.all().order_by("-visit_time")[0].visit_time.date()
        else:
            the_end_date = parse(the_end_date)

        a = AnalystSummary()
        data = a.get_rates_table(
            start_date=the_start_date, end_date=the_end_date,
            service=the_service, clinic=the_clinic)
        content = {"feedback_data": {}}
        for a_rate_row in data:
            content["feedback_data"]["row"+a_rate_row["row_num"].replace(".", "")] = {
                "row_title": a_rate_row["row_title"],
                "rsp_num": a_rate_row["rsp_num"],
                "rsp_prt": "--:--",
                "rsp_srt": "--:--"
            }

        return HttpResponse(json.dumps(content), content_type="text/json")


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
