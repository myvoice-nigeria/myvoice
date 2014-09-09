import json
from operator import attrgetter
import logging

from django.http import HttpResponse
from django.shortcuts import redirect
from django.db.models.aggregates import Min, Max
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.template.loader import get_template
from django.template.context import Context

from myvoice.core.utils import get_week_start, get_week_end, make_percentage
from myvoice.core.utils import get_date, calculate_weeks_ranges
from myvoice.survey import utils as survey_utils
from myvoice.survey.models import Survey, SurveyQuestion, SurveyQuestionResponse

from . import forms
from . import models

from datetime import timedelta

logger = logging.getLogger(__name__)


def hour_to_hr(txt):
    return txt.replace('hour', 'hr')


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

    def get_week_ranges(self, start_date, end_date):
        """
        Break a date range into a group of date ranges representing weeks.
        """
        while start_date <= end_date:
            week_start = get_week_start(start_date)
            week_end = get_week_end(start_date)
            yield week_start, week_end

            if not week_end:
                break
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
            question_type=SurveyQuestion.MULTIPLE_CHOICE).order_by('report_order')
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
            total_resp = responses.filter(question=question).count()
            positive = responses.filter(
                question=question, positive_response=True).count()
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
        max_date = self.responses.aggregate(Max('datetime'))['datetime__max']

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
                # Get rid of percent sign (need to fix)
                if perc:
                    perc = perc.replace('%', '')
                week_data.append((perc, tot))

            # Wait Time
            mode, mode_len = self.get_wait_mode(week_responses)
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

    def get_date_range(self):
        if self.responses:
            min_date = min(self.responses, key=attrgetter('datetime')).datetime
            max_date = max(self.responses, key=attrgetter('datetime')).datetime
            return get_week_start(min_date), get_week_end(max_date)
        return None, None

    def get_detailed_comments(self, start_date="", end_date=""):
        """Combine open-ended survey comments with General Feedback."""
        open_ended_responses = self.responses.filter(
            question__question_type=SurveyQuestion.OPEN_ENDED)

        if start_date:
            open_ended_responses = open_ended_responses.filter(
                datetime__range=(get_date(start_date), get_date(end_date)))

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
        question_labels = [qtn.question_label for qtn in self.questions]
        kwargs['question_labels'] = question_labels
        kwargs['min_date'], kwargs['max_date'] = self.get_date_range()
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
        kwargs['weeks'] = calculate_weeks_ranges(kwargs['min_date'], kwargs['max_date'])

        # TODO - participation rank amongst other clinics.
        return super(ClinicReport, self).get_context_data(**kwargs)


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
        return {
            'num_registered': num_registered,
            'num_started': num_started,
            'perc_started': percent_started,
            'num_completed': num_completed,
            'perc_completed': percent_completed,
            'fos': fos_array
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

    #def calculate_date_range(self):
    #    try:
    #        self.start_date = get_week_start(self.curr_date)
    #        self.end_date = get_week_end(self.curr_date)
    #    except (ValueError, AttributeError):
    #        pass

    def get_object(self, queryset=None):
        obj = super(RegionReport, self).get_object(queryset)
        #self.calculate_date_range()
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
        kwargs['min_date'] = self.start_date
        kwargs['max_date'] = self.end_date
        kwargs['weeks'] = calculate_weeks_ranges(kwargs['min_date'], kwargs['max_date'])
        data = super(RegionReport, self).get_context_data(**kwargs)
        return data

    def get_clinic_labels(self):
        default_labels = [
            'Feedback Participation',
            'Patient Satisfaction',
            'Quality (Score, Q1)',
            'Quantity (Score, Q1)']
        question_labels = [i.question_label for i in self.questions]
        return default_labels + question_labels

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

            # Some dummy data
            clinic_data.append(("Quality", None, 0))
            clinic_data.append(("Quantity", None, 0))

            # Indices for each question
            target_questions = self.questions.exclude(label='Wait Time')
            for index in self.get_indices(target_questions, clinic_responses):
                clinic_data.append(index)

            # Wait Time
            mode, mode_len = self.get_wait_mode(clinic_responses)
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
