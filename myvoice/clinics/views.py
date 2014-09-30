import json
from dateutil.parser import parse
import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView, TemplateView
from django.utils import timezone
from django.db.models.aggregates import Max, Min
from django.template.loader import get_template
from django.template import Context
from django.core.serializers.json import DjangoJSONEncoder

from myvoice.core.utils import get_week_start, get_week_end, make_percentage, daterange
from myvoice.core.utils import get_date, hour_to_hr
from myvoice.survey import utils as survey_utils
from myvoice.survey.models import Survey, SurveyQuestion, SurveyQuestionResponse
from myvoice.clinics.models import Clinic, Service, Visit, GenericFeedback

from . import forms
from . import models

from datetime import timedelta

logger = logging.getLogger(__name__)


class VisitView(View):

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        return super(VisitView, self).dispatch(*args, **kwargs)

    def post(self, request):
        success_msg = "Entry received for patient with serial number {}. Thank you."
        logger.debug("post data is %s" % request.POST)
        form = forms.VisitForm(request.POST)
        if form.is_valid():

            clnc, mobile, serial, serv, txt = form.cleaned_data['text']
            logger.debug("visit form text is {}".format(txt))

            sender = survey_utils.convert_to_local_format(form.cleaned_data['phone'])
            if not sender:
                sender = form.cleaned_data['phone']
            try:
                patient = models.Patient.objects.get(clinic=clnc, serial=serial)
            except models.Patient.DoesNotExist:
                patient = models.Patient.objects.create(
                    clinic=clnc,
                    serial=serial,
                    mobile=mobile)

            output_msg = success_msg.format(serial)
            logger.debug("Output message for serial {0} is {1}".format(serial, output_msg))

            models.Visit.objects.create(patient=patient, service=serv, mobile=mobile, sender=sender)
            data = json.dumps({'text': output_msg})
        else:
            data = json.dumps({'text': self.get_error_msg(form)})

        response = HttpResponse(data, content_type='text/json')

        # This is to test webhooks from localhost
        # response['Access-Control-Allow-Origin'] = '*'
        return response

    def get_error_msg(self, form):
        """Extract the first error message from the form's 'text' field."""
        msgs = ", ".join(form.errors['text'])
        logger.debug("visit form error messages are {}".format(msgs))
        return form.errors['text'][0]


class ClinicReportSelectClinic(FormView):
    template_name = 'clinics/select.html'
    form_class = forms.SelectClinicForm

    def form_valid(self, form):
        clinic = form.cleaned_data['clinic']
        return redirect('clinic_report', slug=clinic.slug)


class ReportMixin(object):

    def start_day(self, dt):
        """Change time to midnight."""
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)

    def get_current_week(self):
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(6)
        start_date = self.start_day(start_date)
        return start_date, end_date

    def get_week_ranges(self, start_date, end_date, curr_date=None):
        """
        Break a date range into a group of date ranges representing weeks.

        If end_date > today, use today as the end_date, and start_date as today-6
        i.e. the last 7 days.
        """
        if not curr_date:
            curr_date = timezone.now()

        if not start_date or not end_date:
            return
        while start_date <= end_date:
            week_start = get_week_start(start_date)
            week_end = get_week_end(start_date)

            # Check if week_end is greater than current date
            if week_end > curr_date:
                date_diff = (week_end.date() - curr_date.date()).days
                week_start = week_start - timedelta(date_diff)
                week_end = week_end - timedelta(date_diff)

            yield week_start, week_end

            start_date = week_end + timezone.timedelta(microseconds=1)

    def get_survey_questions(self, start_date=None, end_date=None):
        if not start_date:
            start_date = get_week_start(timezone.now())
        if not end_date:
            end_date = get_week_end(timezone.now())

        # Make sure start and end are dates not datetimes
        # Note that end_date is going to be truncated
        # (2014, 1, 12, 23, 59, 59, 999999) -> (2014, 1, 12)
        # Because the input is (indirectly) got from get_week_ranges.
        start_date = start_date.date()
        end_date = end_date.date()
        qtns = SurveyQuestion.objects.exclude(start_date__gt=end_date).exclude(
            end_date__lt=end_date).filter(
            question_type=SurveyQuestion.MULTIPLE_CHOICE).order_by(
            'report_order').select_related('display_label')
        return qtns

    def initialize_data(self):
        """Called by get_object to initialize state information."""
        self.survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
        self.questions = self.get_survey_questions()

    def get_wait_mode(self, responses):
        """Get most frequent wait time and the count for that wait time."""
        responses = responses.filter(
            question__label='Wait Time').values_list('response', flat=True)
        categories = SurveyQuestion.objects.get(label='Wait Time').get_categories()
        mode = survey_utils.get_mode(responses, categories)
        len_mode = len([i for i in responses if i == mode])
        return mode, len_mode

    def get_indices(self, target_questions, responses):
        """Get % and count of positive responses per question."""
        for question in target_questions:
            question_responses = [r for r in responses if r.question_id == question.pk]
            total_resp = len(question_responses)
            positive = len([r for r in question_responses if r.positive_response])
            percent = '{}%'.format(
                make_percentage(positive, total_resp)) if total_resp else None
            yield (question.question_label, percent, positive)

    def get_satisfaction_counts(self, responses):
        """Return satisfaction percentage and total of survey participants."""
        responses = responses.filter(question__for_satisfaction=True)
        total = responses.distinct('visit').count()
        unsatisfied = responses.exclude(positive_response=True).distinct('visit').count()

        if not total:
            return None, 0

        return 100 - make_percentage(unsatisfied, total), total-unsatisfied

    def get_feedback_participation(self, visits):
        """Return % of surveys responded to total visits."""
        survey_started = visits.filter(survey_started=True).count()
        total_visits = visits.count()

        if total_visits:
            survey_percent = make_percentage(survey_started, total_visits)
        else:
            survey_percent = None
        return survey_percent, survey_started

    def get_feedback_by_service(self):
        """Return analyzed feedback by service then question."""
        data = []

        responses = self.responses.exclude(service=None)
        target_questions = self.questions.exclude(label='Wait Time')

        services = models.Service.objects.all()
        for service in services:
            service_data = []
            service_responses = responses.filter(service=service)
            for result in self.get_indices(target_questions, service_responses):
                service_data.append(result)

            # Wait Time
            mode, mode_len = self.get_wait_mode(service_responses)
            if mode:
                mode = hour_to_hr(mode)
            service_data.append(('Wait Time', mode, mode_len))

            data.append((service, service_data))
        return data


class ClinicReport(ReportMixin, DetailView):
    template_name = 'clinics/report.html'
    model = models.Clinic

    def get_object(self, queryset=None):
        obj = super(ClinicReport, self).get_object(queryset)
        self.responses = obj.surveyquestionresponse_set.filter(display_on_dashboard=True)
        self.responses = self.responses.select_related('question', 'service', 'visit')
        self.visits = models.Visit.objects.filter(
            patient__clinic=obj, survey_sent__isnull=False)
        self.initialize_data()
        self.generic_feedback = obj.genericfeedback_set.filter(display_on_dashboard=True)
        return obj

    def get_feedback_by_week(self):
        data = []

        visits = self.visits.filter(survey_started=True)
        min_date = self.responses.aggregate(Min('datetime'))['datetime__min']
        max_date = timezone.now()

        week_ranges = self.get_week_ranges(min_date, max_date)

        for start_date, end_date in week_ranges:
            week_responses = self.responses.filter(datetime__range=(start_date, end_date))
            week_data = []

            # Get number of surveys started in this week
            survey_num = visits.filter(
                visit_time__range=(start_date, end_date)).count()

            # Get patient satisfaction, throw away total we need just percent
            satis_percent, _ = self.get_satisfaction_counts(week_responses)

            # Get indices for each question
            questions = self.get_survey_questions(start_date, end_date).exclude(
                label='Wait Time')
            for label, perc, tot in self.get_indices(questions, week_responses):
                # FIXME: Get rid of percent sign (need to fix)
                if perc:
                    perc = perc.replace('%', '')
                week_data.append((perc, tot))

            # Wait Time
            mode, mode_len = self.get_wait_mode(week_responses)
            if mode:
                mode = hour_to_hr(mode)
            labels = [qtn.question_label.replace(' ', '\\n') for qtn in questions]

            data.append({
                'week_start': start_date,
                'week_end': end_date,
                'data': week_data,
                'patient_satisfaction': satis_percent,
                'wait_time_mode': mode,
                'survey_num': survey_num,
                'question_labels': labels
            })
        return data

    def get_detailed_comments(self, start_date=None, end_date=None):
        """Combine open-ended survey comments with General Feedback."""
        open_ended_responses = self.responses.filter(
            question__question_type=SurveyQuestion.OPEN_ENDED)

        if start_date:
            open_ended_responses = open_ended_responses.filter(
                datetime__range=(get_date(start_date), get_date(end_date)))

        comments = [
            {
                'question': r.question.question_label,
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
        question_labels = [qtn.question_label for qtn in self.questions]
        kwargs['question_labels'] = question_labels

        if self.responses:
            min_date = self.responses.aggregate(Min('datetime'))['datetime__min']
            kwargs['min_date'] = get_week_start(min_date)
            kwargs['max_date'] = timezone.now()
        else:
            kwargs['min_date'] = None
            kwargs['max_date'] = None

        num_registered = self.visits.count()
        num_started = self.visits.filter(survey_started=True).count()
        num_completed = self.visits.filter(survey_completed=True).count()

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

        kwargs['week_ranges'] = [
            (self.start_day(start), self.start_day(end)) for start, end in
            self.get_week_ranges(kwargs['min_date'], kwargs['max_date'])]
        kwargs['week_start'], kwargs['week_end'] = self.get_current_week()

        # TODO - participation rank amongst other clinics.
        return super(ClinicReport, self).get_context_data(**kwargs)


class AnalystSummary(TemplateView):
    template_name = 'analysts/analysts.html'
    allowed_methods = ['get', 'post', 'put', 'delete', 'options']

    def options(self, request, id):
        response = HttpResponse()
        response['allow'] = ','.join([self.allowed_methods])
        return response

    @classmethod
    def get_visit_counts(cls, clinics, **kwargs):
        """Get the count of visits to each of clinics for service
        and between start_date and end_date.

        Return dict of clinic: count_of_visits."""
        visit_counts = {}
        start_date = kwargs.get('start_date', None)
        end_date = kwargs.get('end_date', None)
        service = kwargs.get('service', None)

        # Build filter params
        params = {'survey_sent__isnull': False}
        if service:
            params.update({'service__name': service})
        if start_date:
            params.update({'visit_time__gte': start_date})
        if end_date:
            params.update({'visit_time__lte': end_date})

        visits = models.Visit.objects.filter(**params)

        for clinic in clinics:
            visit_counts.update({clinic: visits.filter(patient__clinic=clinic).count()})
        return visit_counts

    @classmethod
    def get_survey_counts(cls, qset, clinics, **kwargs):
        """Get the count of surveys for each clinic for service,
        and between start_date and end_date.

        Return dict of clinic: count_of_started survey."""
        counts = {}

        start_date = kwargs.get('start_date', None)
        end_date = kwargs.get('end_date', None)
        service = kwargs.get('service', None)

        # Build filter params and apply to qset
        params = {}
        if service:
            params.update({'service': service})
        if start_date:
            params.update({'visit__visit_time__gte': start_date})
        if end_date:
            params.update({'visit__visit_time__lte': end_date})

        qset = qset.filter(**params)

        for clinic in clinics:
            counts.update({clinic: qset.filter(clinic=clinic).count()})
        return counts

    def get_completion_table(self, start_date=None, end_date=None, service=None):
        completion_table = []
        st_total = 0            # Surveys Triggered
        ss_total = 0            # Surveys Started
        sc_total = 0            # Surveys Completed

        # All Clinics to Loop Through, build our own dict of data
        all_clinics = Clinic.objects.all().order_by("name")

        # Build params for to filter by start_date, end_date and service
        visit_params = {'survey_sent__isnull': False}
        survey_params = {}
        if start_date and isinstance(start_date, basestring):
            visit_params.update({'visit_time__gte': parse(start_date)})
            survey_params.update({'visit__visit_time__gte': parse(start_date)})
        if end_date and isinstance(end_date, basestring):
            visit_params.update({'visit_time__lte': parse(end_date)})
            survey_params.update({'visit__visit_time_lte': parse(end_date)})
        if service and isinstance(service, basestring):
            visit_params.update({'service__name': service})
            survey_params.update({'service__name': service})

        visit_counts = self.get_visit_counts(all_clinics, **visit_params)
        started_qset = SurveyQuestionResponse.objects.filter(
            question__label__iexact='Open Facility',
            question__question_type__iexact='multiple-choice')
        started_counts = self.get_survey_counts(started_qset, all_clinics, **survey_params)
        # Loop through the Clinics, summating the data required.
        for a_clinic in clinics_to_add:

            survey_responses = SurveyQuestionResponse.objects.all()

            if start_date:
                survey_responses = survey_responses.filter(visit__visit_time__gte=start_date)
            if end_date:
                survey_responses = survey_responses.filter(visit__visit_time__lte=end_date)
            if service:
                survey_responses = survey_responses.filter(service__name__iexact=service)

            survey_responses = survey_responses.filter(clinic=a_clinic)

            # Surveys Triggered Query Statistics
            st_count = survey_responses.filter(visit__survey_sent__isnull=False).count()
            st_total += st_count

            survey_responses = survey_responses.filter(question__label__iexact="Open Facility")\
                .filter(question__question_type__iexact="multiple-choice")

            # Survey Started Query Statistics
            ss_count = survey_responses.filter(visit__survey_started=True).count()
            ss_total += ss_count

            # Survey Completed Query Statistics
            sc_count = survey_responses.filter(visit__survey_completed=True).count()
            sc_total += sc_count

            # Survey Percentages
            if st_count:
                ss_st_percent = 100*ss_count/st_count
                sc_st_percent = 100*sc_count/st_count
            else:
                ss_st_percent = 0
                sc_st_percent = 0

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
            ss_st_percent_total = 0
            sc_st_percent_total = 0

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
        if isinstance(start_date, basestring):
            start_date = parse(start_date)
        if isinstance(end_date, basestring):
            end_date = parse(end_date)
        for single_date in daterange(start_date, end_date):
            return_dates.append(single_date)
        return return_dates

    def get_survey_question_responses(self):
        return SurveyQuestionResponse.objects.all()

    def get_surveys_triggered_summary(self):
        """Total number of Surveys Triggered."""
        return Visit.objects.filter(survey_sent__isnull=False)

    def get_surveys_started_summary(self):
        return SurveyQuestionResponse.objects.filter(
            question__question_type__iexact="open-ended")

    def get_surveys_completed_summary(self):
        """Total number of Surveys Completed."""
        return SurveyQuestionResponse.objects.filter(question__label__iexact="Wait Time")

    def get_context_data(self, **kwargs):

        context = super(AnalystSummary, self).\
            get_context_data(**kwargs)


        the_start_date = Visit.objects.all().order_by("visit_time")[0].visit_time.date()
        the_end_date = Visit.objects.all().order_by("-visit_time")[0].visit_time.date()

        context['completion_table'] = self.get_completion_table(
            start_date=the_start_date, end_date=the_end_date)

        context['responses'] = self.get_survey_question_responses()
#        context['completion_table'] = self.get_completion_table()

        context['st'] = self.get_surveys_triggered_summary()
        context['st_count'] = context['st'].count()

        # context['ss'] = self.get_surveys_started_summary()
        # context['ss_count'] = survey_utils.get_started_count(survey_responses)
        context['ss'] = Visit.objects.all().filter(survey_started=True)
        context["ss_count"] = context["ss"].count()

        # context['sc'] = self.get_surveys_completed_summary()
        # context['sc_count'] = context['sc'].count()
        context['sc'] = Visit.objects.all().filter(survey_completed=True)
        context['sc_count'] = context['sc'].count()

        if context['ss_count']:
            context['ss_st_percent'] = 100*context['ss_count']/context['st_count']
        else:
            context['ss_st_percent'] = 0

        if context['st_count']:
            context['sc_st_percent'] = 100*context['sc_count']/context['st_count']
        else:
            context['sc_st_percent'] = 0

        # Needed for to populate the Dropdowns (Selects)
        context['services'] = Service.objects.all()
        first_date = Visit.objects.aggregate(Min('visit_time'))['visit_time__min'].date()
        last_date = Visit.objects.aggregate(Max('visit_time'))['visit_time__max'].date()
        context['date_range'] = self.get_date_range(first_date, last_date)
        context['clinics'] = Clinic.objects.all().order_by("name")
        context['gfb_count'] = GenericFeedback.objects.all().count()
        return context


class FilterMixin(object):

    def get_variable(self, request, variable_name, ignore_value):
        data = request.GET.get(variable_name, ignore_value)
        if not data or data == ignore_value:
            return None
        return data


class CompletionFilter(FilterMixin, View):

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
                "ssp": a_clinic['ss_st_percent'],
                "sc": a_clinic["sc_count"],
                "scp": a_clinic["sc_st_percent"]
            }

        return HttpResponse(json.dumps(content), content_type="text/json")



class FeedbackFilter(FilterMixin, View):

    def get(self, request):
        the_service = self.get_variable(request, "service", "Service")
        the_clinic = self.get_variable(request, "clinic", "Clinic")
        the_start_date = self.get_variable(request, "start_date", "Start Date")
        the_end_date = self.get_variable(request, "end_date", "End Date")

        qset = SurveyQuestionResponse.objects.all()
        responses = survey_utils.filter_sqr_query(
            qset, clinic=the_clinic, service=the_service,
            start_date=the_start_date, end_date=the_end_date)

        # Render template with responses as context
        tmpl = get_template('analysts/_rates.html')
        ctx = Context({'responses': responses})
        html = tmpl.render(ctx)
        return HttpResponse(html, content_type='text/html')


class ClinicReportFilterByWeek(ReportMixin, DetailView):

    def get_feedback_data(self, start_date, end_date, clinic):
        report = ClinicReport()
        report.object = clinic

        report.start_date = start_date
        report.end_date = end_date
        report.curr_date = report.end_date

        # Calculate the Data for Feedback on Services (later summarized as 'fos')
        report.responses = SurveyQuestionResponse.objects.filter(
            clinic__id=report.object.id, datetime__gte=report.start_date,
            datetime__lte=report.end_date+timedelta(1))

        report.questions = self.get_survey_questions(start_date, end_date)
        fos = report.get_feedback_by_service()

        fos_array = []
        for row in fos:
            new_row = (row[0].name, row[1])
            fos_array.append(new_row)

        # Calculate the Survey Participation Data via week filter
        num_registered = survey_utils.get_registration_count(
            report.object, report.start_date, report.end_date)
        num_started = survey_utils.get_started_count(report.responses)
        num_completed = survey_utils.get_completion_count(report.responses)

        if num_registered:
            percent_started = make_percentage(num_started, num_registered)
            percent_completed = make_percentage(num_completed, num_registered)
        else:
            percent_completed = None
            percent_started = None

        # Render template for table
        tmpl = get_template('clinics/report_service.html')
        questions = report.get_survey_questions(start_date, end_date)
        cntxt = Context(
            {
                'feedback_by_service': fos,
                'question_labels': [qtn.question_label for qtn in questions],
                'min_date': start_date,
                'max_date': end_date
            })
        html = tmpl.render(cntxt)

        return {
            'num_registered': num_registered,
            'num_started': num_started,
            'perc_started': percent_started,
            'num_completed': num_completed,
            'perc_completed': percent_completed,
            'fos': fos_array,
            'fos_html': html
        }

    def get(self, request, *args, **kwargs):

        # Get the variables from the ajax request

        _start_date = request.GET.get('start_date')
        _end_date = request.GET.get('end_date')
        clinic_id = request.GET.get('clinic_id')

        if not all((_start_date, _end_date, clinic_id)):
            return HttpResponse('')

        start_date = get_date(_start_date)
        end_date = get_date(_end_date)

        # Create an instance of a ClinicReport
        clinic = models.Clinic.objects.get(id=clinic_id)

        # Collect the Comments filtered by the weeks
        clinic_data = self.get_feedback_data(start_date, end_date, clinic)

        return HttpResponse(
            json.dumps(clinic_data, cls=DjangoJSONEncoder), content_type='text/json')


class RegionReport(ReportMixin, DetailView):
    template_name = 'clinics/summary.html'
    model = models.Region

    def __init__(self, *args, **kwargs):
        super(RegionReport, self).__init__(*args, **kwargs)
        self.curr_date = None
        self.start_date = None
        self.end_date = None
        self.weeks = None

    def get_object(self, queryset=None):
        obj = super(RegionReport, self).get_object(queryset)
        self.responses = SurveyQuestionResponse.objects.filter(clinic__lga__iexact=obj.name)
        if self.start_date and self.end_date:
            self.responses = self.responses.filter(
                visit__visit_time__range=(self.start_date, self.end_date))
        self.responses = self.responses.select_related('question', 'service', 'visit')
        self.initialize_data()
        return obj

    def get_context_data(self, **kwargs):
        kwargs['responses'] = self.responses
        kwargs['feedback_by_service'] = self.get_feedback_by_service()
        kwargs['feedback_by_clinic'] = self.get_feedback_by_clinic()
        kwargs['service_labels'] = [i.question_label for i in self.questions]
        kwargs['clinic_labels'] = self.get_clinic_labels()

        if self.responses:
            min_date = self.responses.aggregate(Min('datetime'))['datetime__min']
            kwargs['min_date'] = get_week_start(min_date)
            kwargs['max_date'] = timezone.now()
        else:
            kwargs['min_date'] = None
            kwargs['max_date'] = None

        kwargs['week_ranges'] = [
            (self.start_day(start), self.start_day(end)) for start, end in
            self.get_week_ranges(kwargs['min_date'], kwargs['max_date'])]
        kwargs['week_start'], kwargs['week_end'] = self.get_current_week()
        data = super(RegionReport, self).get_context_data(**kwargs)
        return data

    def get_clinic_labels(self):
        default_labels = [
            'Feedback Participation',
            'Patient Satisfaction',
            'Quality - Q2 2014 (%)',
            'Quantity - Q2 2014 (N)']
        question_labels = [i.question_label for i in self.questions]
        return default_labels + question_labels

    def get_clinic_score(self, clinic, ref_date=None):
        """Return quality and quantity scores for the clinic and quarter in which
        ref_date is in."""
        if not ref_date:
            ref_date = timezone.datetime.now().date()
        try:
            score = models.ClinicScore.objects.get(
                clinic=clinic, start_date__lte=ref_date, end_date__gte=ref_date)
        except (models.ClinicScore.DoesNotExist, models.ClinicScore.MultipleObjectsReturned):
            return None
        else:
            return score

    def get_feedback_by_clinic(self):
        """Return analyzed feedback by clinic then question."""
        data = []

        responses = self.responses.filter(question__in=self.questions)
        visits = models.Visit.objects.filter(survey_sent__isnull=False)

        if self.start_date and self.end_date:
            responses = responses.filter(
                visit__visit_time__range=(self.start_date, self.end_date))
            visits = visits.filter(visit_time__range=(self.start_date, self.end_date))

        for clinic in models.Clinic.objects.all():
            clinic_data = []
            clinic_responses = responses.filter(clinic=clinic)
            clinic_visits = visits.filter(patient__clinic=clinic)
            # Get feedback participation
            part_percent, part_total = self.get_feedback_participation(clinic_visits)
            if part_percent is not None:
                part_percent = '{}%'.format(part_percent)
            clinic_data.append(
                ('Participation', part_percent, part_total))

            # Get patient satisfaction
            satis_percent, satis_total = self.get_satisfaction_counts(clinic_responses)
            if satis_percent is not None:
                satis_percent = '{}%'.format(satis_percent)
            clinic_data.append(
                ('Patient Satisfaction', satis_percent, satis_total))

            # Quality and quantity scores
            if self.start_date:
                score_date = self.start_date
            else:
                score_date = None
            score = self.get_clinic_score(clinic, score_date)
            if not score:
                clinic_data.append(("Quality", None, 0))
                clinic_data.append(("Quantity", None, 0))
            else:
                clinic_data.append(("Quality", "{}%".format(score.quality), ""))
                clinic_data.append(("Quantity", "{}".format(score.quantity), ""))

            # Indices for each question
            target_questions = self.questions.exclude(label='Wait Time')
            for index in self.get_indices(target_questions, clinic_responses):
                clinic_data.append(index)

            # Wait Time
            mode, mode_len = self.get_wait_mode(clinic_responses)
            if mode:
                mode = hour_to_hr(mode)
            clinic_data.append(('Wait Time', mode, mode_len))

            data.append((clinic.id, clinic.name, clinic_data))

        return data


class LGAReportFilterByService(View):

    def get_feedback_data(self, report, start_date, end_date):
        # FIXME: Need to filter by the lga
        report.responses = SurveyQuestionResponse.objects.filter(
            visit__visit_time__range=(start_date, end_date))
        report.initialize_data()

        return report.get_feedback_by_service()

    def get(self, request):

        _start_date = request.GET.get('start_date')
        _end_date = request.GET.get('end_date')

        if not all((_start_date, _end_date)):
            return HttpResponse('')

        start_date = get_date(_start_date)
        end_date = get_date(_end_date)

        report = ReportMixin()

        feedback_data = self.get_feedback_data(report, start_date, end_date)
        questions = report.get_survey_questions(start_date, end_date)
        data = {
            'feedback_by_service': feedback_data,
            'min_date': start_date,
            'max_date': end_date,
            'service_labels': [i.question_label for i in questions]
        }

        # Render template
        tmpl = get_template('clinics/by_service.html')
        cntxt = Context(data)
        html = tmpl.render(cntxt)

        return HttpResponse(html, content_type="text/html")


class LGAReportFilterByClinic(View):

    def get_feedback_data(self, report, start_date, end_date):
        report.start_date = start_date
        report.end_date = end_date
        report.responses = SurveyQuestionResponse.objects.filter(
            visit__visit_time__range=(start_date, end_date))
        report.initialize_data()
        report.questions = report.get_survey_questions(start_date, end_date)

        return report.get_feedback_by_clinic()

    def get(self, request):

        # Get the variables
        _start_date = request.GET.get('start_date')
        _end_date = request.GET.get('end_date')

        if not all((_start_date, _end_date)):
            return HttpResponse('')

        start_date = get_date(_start_date)
        end_date = get_date(_end_date)

        report = RegionReport()

        feedback_data = self.get_feedback_data(report, start_date, end_date)
        data = {
            'feedback_by_clinic': feedback_data,
            'min_date': start_date,
            'max_date': end_date,
            'clinic_labels': report.get_clinic_labels()
        }

        # Render template
        tmpl = get_template('clinics/by_clinic.html')
        cntxt = Context(data)
        html = tmpl.render(cntxt)

        return HttpResponse(html, content_type="text/html")


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
