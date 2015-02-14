import json
from dateutil.parser import parse
import logging
from datetime import timedelta
from collections import Counter

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import DetailView, View, FormView, TemplateView
from django.utils import timezone
from django.db.models.aggregates import Min, Sum
from django.template.loader import get_template
from django.template import Context
from django.core.serializers.json import DjangoJSONEncoder

from myvoice.core.utils import get_week_start, get_week_end, make_percentage
from myvoice.core.utils import get_date, hour_to_hr, compress_list
from myvoice.survey import utils as survey_utils
from myvoice.survey.models import Survey, SurveyQuestion, SurveyQuestionResponse
from myvoice.clinics.models import Clinic, Service, GenericFeedback

from . import forms
from . import models
from . import pdf


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
            perc = make_percentage(positive, total_resp) if total_resp else 0
            yield (question.question_label, perc, positive)

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

    def get_feedback_statistics(self, clinics, **kwargs):
        """Return dict of surveys_sent, surveys_started and surveys_completed.

        kwargs are service, start_date, end_date."""
        visits = models.Visit.objects.filter(patient__clinic__in=clinics)
        if kwargs.get('start_date') and kwargs.get('end_date'):
            end_date = kwargs['end_date'] + timedelta(1)
            visits = visits.filter(
                visit_time__gte=kwargs['start_date'],
                visit_time__lt=end_date)
        if 'service' in kwargs:
            visits = visits.filter(service=kwargs['service'])

        sent = list(visits.filter(survey_sent__isnull=False).values_list(
            'patient__clinic', flat=True))
        started = list(visits.filter(survey_started=True).values_list(
            'patient__clinic', flat=True))
        completed = list(visits.filter(survey_completed=True).values_list(
            'patient__clinic', flat=True))

        _sent = [sent.count(clinic.pk) for clinic in clinics]
        _started = [started.count(clinic.pk) for clinic in clinics]
        _completed = [completed.count(clinic.pk) for clinic in clinics]
        return {
            'sent': _sent,
            'started': _started,
            'completed': _completed,
            }

    def get_response_statistics(self, clinics, questions, start_date=None, end_date=None):
        """Get total and %ge of +ve responses to questions in clinics."""
        responses = SurveyQuestionResponse.objects.filter(clinic__in=clinics)
        if start_date and end_date:
            responses = responses.filter(visit__visit_time__range=(start_date, end_date))
        return [(i[2], i[1]) for i in self.get_indices(questions, responses)]

    def get_feedback_by_service(self):
        """Return analyzed feedback by service then question."""
        data = []

        responses = self.responses.exclude(service=None)
        target_questions = self.questions.exclude(label='Wait Time')

        services = models.Service.objects.all()
        for service in services:
            service_data = []
            service_responses = responses.filter(service=service)
            for label, perc, val in self.get_indices(target_questions, service_responses):
                if perc or perc == 0:
                    perc = '{}%'.format(perc)
                service_data.append((label, val, perc))

            # Wait Time
            mode, mode_len = self.get_wait_mode(service_responses)
            if mode:
                mode = hour_to_hr(mode)
            service_data.append(('Wait Time', mode, mode_len))

            data.append((service, service_data))
        return data

    def get_feedback_by_clinic(self, clinics, start_date=None, end_date=None):
        """Return analyzed feedback by clinic then question."""
        data = []

        responses = self.responses.filter(question__in=self.questions)
        visits = models.Visit.objects.filter(
            survey_sent__isnull=False, patient__clinic__in=clinics)

        if start_date and end_date:
            responses = responses.filter(
                visit__visit_time__range=(start_date, end_date))
            visits = visits.filter(visit_time__range=(start_date, end_date))

        for clinic in clinics:
            clinic_data = []
            clinic_responses = responses.filter(clinic=clinic)
            clinic_visits = visits.filter(patient__clinic=clinic)
            # Get feedback participation
            part_percent, part_total = self.get_feedback_participation(clinic_visits)
            if part_percent is not None:
                part_percent = '{}%'.format(part_percent)
            clinic_data.append(
                ('Participation', part_total, part_percent))

            # Quality and quantity scores
            score_date = start_date if start_date else None
            score = self.get_clinic_score(clinic, score_date)
            if not score:
                clinic_data.append(("Quality", None, 0))
                clinic_data.append(("Quantity", None, 0))
            else:
                clinic_data.append(("Quality", "{}%".format(score.quality), ""))
                clinic_data.append(("Quantity", "{}".format(score.quantity), ""))

            # Indices for each question
            target_questions = self.questions.exclude(label='Wait Time')
            for label, perc, val in self.get_indices(target_questions, clinic_responses):
                if perc or perc == 0:
                    perc = '{}%'.format(perc)
                clinic_data.append((label, val, perc))

            # Wait Time
            mode, mode_len = self.get_wait_mode(clinic_responses)
            if mode:
                mode = hour_to_hr(mode)
            clinic_data.append(('Wait Time', mode, mode_len))

            data.append((clinic.id, clinic.name, clinic_data))

        return data

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

    def get_main_comments(self, clinics):
        """Get generic comments marked to show on summary pages."""
        comments = [
            (cmt.message, cmt.report_count)
            for cmt in models.GenericFeedback.objects.filter(
                clinic__in=clinics, display_on_summary=True)]
        return comments

    def get_clinic_labels(self):
        default_labels = [
            'Feedback Participation',
            'Quality - Q2 2014 (%)',
            'Quantity - Q2 2014 (N)']
        question_labels = [i.question_label for i in self.questions]
        return default_labels + question_labels

    def format_chart_labels(self, labels, async=False):
        """Replaces space with newline."""
        return ['\n'.join(str(x).split()) for x in labels]

    def get_manual_registrations(self, clinics, **kwargs):
        """Get the total of manual registrations by clinics between date range."""
        manual_regs = models.ManualRegistration.objects.filter(clinic__in=clinics)
        if 'start_date' in kwargs and 'end_date' in kwargs:
            manual_regs = manual_regs.filter(
                entry_date__gte=kwargs['start_date'],
                entry_date__lte=kwargs['end_date'])

        return [manual_regs.filter(clinic=clinic).aggregate(
            Sum('visit_count'))['visit_count__sum'] or 0
            for clinic in clinics]


class ClinicReport(ReportMixin, DetailView):
    template_name = 'clinics/report.html'
    model = models.Clinic

    def __init__(self, *args, **kwargs):
        super(ClinicReport, self).__init__(*args, **kwargs)
        self.start_date = None
        self.end_date = None

    def get_object(self, queryset=None):
        obj = super(ClinicReport, self).get_object(queryset)
        self.responses = obj.surveyquestionresponse_set.filter(display_on_dashboard=True)
        self.visits = models.Visit.objects.filter(patient__clinic=obj, survey_sent__isnull=False)
        if self.start_date and self.end_date:
            self.responses = self.responses.filter(
                datetime__gte=self.start_date, datetime__lte=self.end_date)
            self.visits = self.visits.filter(
                visit_time__gte=self.start_date, visit_time__lt=self.end_date)
        self.responses = self.responses.select_related('question', 'service', 'visit')
        self.survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
        self.questions = self.get_survey_questions(self.start_date, self.end_date)
        self.generic_feedback = obj.genericfeedback_set.filter(display_on_dashboard=True)
        self.lga_clinics = self.model.objects.filter(lga=obj.lga)
        return obj

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
        kwargs['question_labels'] = [q.question_label for q in self.questions]

        if not (self.start_date and self.end_date) and self.responses:
            min_date = self.responses.aggregate(Min('datetime'))['datetime__min']
            kwargs['min_date'] = get_week_start(min_date)
            kwargs['max_date'] = timezone.now()
        else:
            kwargs['min_date'] = self.start_date
            kwargs['max_date'] = (self.end_date - timedelta(1)) if self.end_date else None

        # Feedback stats for chart
        feedback_stats = self.get_feedback_statistics(
            self.lga_clinics, start_date=self.start_date, end_date=self.end_date)
        kwargs['feedback_stats'] = feedback_stats
        kwargs['max_chart_value'] = max(feedback_stats['sent'])
        kwargs['feedback_clinics'] = self.format_chart_labels(self.lga_clinics)

        # Patient feedback responses
        other_clinics = self.lga_clinics.exclude(pk=self.object.pk)
        current_clinic_stats = self.get_response_statistics(
            (self.object,), self.questions, self.start_date, self.end_date)
        other_stats = self.get_response_statistics(
            other_clinics, self.questions, self.start_date, self.end_date)
        margins = [(x[1] - y[1]) for x, y
                   in zip(current_clinic_stats, other_stats)]
        kwargs['response_stats'] = zip(self.questions, current_clinic_stats, other_stats, margins)

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

        # TODO - participation rank amongst other clinics.
        return super(ClinicReport, self).get_context_data(**kwargs)


class AnalystSummary(TemplateView, ReportMixin):
    template_name = 'analysts/analysts.html'
    allowed_methods = ['get', 'post', 'put', 'delete', 'options']

    def options(self, request, id):
        response = HttpResponse()
        response['allow'] = ','.join([self.allowed_methods])
        return response

    def get_facility_participation(self, clinics, **kwargs):
        """Get the sent, started and completed survey counts for
        clinics, service, dates.

        kwargs = start_date, end_date, service"""
        stats = self.get_feedback_statistics(clinics, **kwargs)
        sent, started, completed = stats['sent'], stats['started'], stats['completed']
        manual_reg = self.get_manual_registrations(clinics, **kwargs)

        sum_manual_reg = sum(manual_reg)
        avg_manual_reg = sum(manual_reg)/len(manual_reg)

        sum_sent = sum(sent)
        avg_sent = sum(sent)/len(sent)

        sum_started = sum(started)
        avg_started = sum(started)/len(started)

        sum_completed = sum(completed)
        avg_completed = sum(completed)/len(completed)

        manual_reg.extend([sum_manual_reg, avg_manual_reg])
        sent.extend([sum_sent, avg_sent])
        started.extend([sum_started, avg_started])
        completed.extend([sum_completed, avg_completed])

        manual_perc = [make_percentage(num, den) for num, den in zip(sent, manual_reg)]
        start_perc = [make_percentage(num, den) for num, den in zip(started, sent)]
        comp_perc = [make_percentage(num, den) for num, den in zip(completed, sent)]
        names = [clinic.name for clinic in clinics] + ['Total', 'Avg']

        return zip(names, manual_perc, sent, started, start_perc, completed, comp_perc)

    def count_by_date(self, qset, dates, datetime_fld):
        """Counts the objects in qset per date using the date_field.

        qset is a queryset
        dates is a list of datetime.date
        datetime_fld is the datetime field in the obj to use in aggregating.
        """
        counted = Counter(tm.date() for tm in qset.values_list(datetime_fld, flat=True))
        return [counted.get(dt, 0) for dt in dates]

    def get_feedback_by_date(self, max_length=10, **kwargs):
        """Returns dict of surveys sent, surveys started, generic feedback by date.

        kwargs are clinics, service, start_date, end_date
        max_length is the maximum number of elements in each list returned."""
        default_end = timezone.now().date()
        default_start = default_end - timedelta(6)
        end_date = kwargs.get('end_date', default_end)
        start_date = kwargs.get('start_date', default_start)

        # We want dates not datetimes
        if isinstance(start_date, timezone.datetime):
            start_date = start_date.date()
        if isinstance(end_date, timezone.datetime):
            end_date = end_date.date()
        date_range = [
            (start_date + timedelta(idx))
            for idx in range((end_date-start_date).days + 1)]

        # Add 1 to end_date so it captures visits of today
        end_plus = end_date + timedelta(1)

        visits = models.Visit.objects.filter(survey_sent__isnull=False)
        generic_feedback = models.GenericFeedback.objects.filter(
            message_date__gte=start_date, message_date__lt=end_plus)
        if 'clinic' in kwargs:
            visits = visits.filter(patient__clinic__name=kwargs['clinic'])
            generic_feedback = generic_feedback.filter(clinic__name=kwargs['clinic'])
        if 'service' in kwargs:
            visits = visits.filter(service__name=kwargs['service'])

        visits = visits.filter(visit_time__gte=start_date, visit_time__lt=end_plus)
        # generic_feedback = generic_feedback.filter(
        #    message_date__gte=start_date, message_date__lt=end_plus)
        started_visits = visits.filter(survey_started=True)

        _dates = compress_list(
            [dt.strftime('%d %b') for dt in date_range], max_length)
        _sent = compress_list(
            self.count_by_date(visits, date_range, 'visit_time'), max_length)
        _started = compress_list(
            self.count_by_date(started_visits, date_range, 'visit_time'), max_length)
        _generic = compress_list(
            self.count_by_date(generic_feedback, date_range, 'message_date'), max_length)
        return {
            'dates': _dates,
            'sent': _sent,
            'started': _started,
            'generic': _generic,
            'max_val': max(_sent + _started + _generic),
        }

    def extract_request_params(self, request_obj):
        """Process request parameters and return a dict.

        kwargs include clinic, service, start_date, end_date."""
        out = {}
        for param in ['clinic', 'service', 'start_date', 'end_date']:
            val = request_obj.GET.get(param)
            if val:
                # Don't forget to parse datetime values
                if param in ['start_date', 'end_date']:
                    val = parse(val)
                out.update({param: val})
        return out

    def get_context_data(self, **kwargs):

        context = super(AnalystSummary, self).get_context_data(**kwargs)

        # FIXME: Need to filter by LGA
        clinics = Clinic.objects.all()
        # Use last week for default date range
        today = timezone.now()
        end_date = today.date()
        start_date = end_date - timedelta(6)

        context['participation'] = self.get_facility_participation(
            clinics, start_date=start_date, end_date=end_date)

        [context.update({k: v}) for k, v in self.get_feedback_by_date(
            start_date=start_date, end_date=end_date).iteritems()]

        # Needed for to populate the Dropdowns (Selects)
        context['services'] = Service.objects.all()
        context['min_date'] = start_date
        context['max_date'] = end_date
        context['clinics'] = clinics
        context['gfb_count'] = GenericFeedback.objects.all().count()
        return context


class ParticipationAsync(View):

    def get(self, request):

        summary = AnalystSummary()
        params = summary.extract_request_params(request)
        if 'clinic' in params:
            clinic = params.pop('clinic')
            clinics = [clinic]
        else:
            # FIXME: Need to filter by LGA
            clinics = Clinic.objects.all()
        participation = summary.get_facility_participation(clinics, **params)

        # Render template with responses as context
        tmpl = get_template('analysts/_facility.html')
        ctx = Context({'participation': participation})
        html = tmpl.render(ctx)
        return HttpResponse(html, content_type='text/html')


class ParticipationCharts(View):

    def get(self, request):

        summary = AnalystSummary()
        params = summary.extract_request_params(request)
        feedback = summary.get_feedback_by_date(**params)

        return HttpResponse(
            json.dumps(feedback, cls=DjangoJSONEncoder), content_type='text/json')


class ClinicReportFilterByWeek(View):

    def get_feedback_data(self, start_date, end_date, clinic_id):
        report = ClinicReport()
        report.start_date = start_date
        report.end_date = end_date
        report.kwargs = {'pk': clinic_id}
        report.object = report.get_object()

        context = report.get_context_data()

        # Render template for feedback on services:
        tmpl = get_template('clinics/report_service.html')
        feedback_by_service_html = tmpl.render(Context({
            'question_labels': context['question_labels'],
            'feedback_by_service': context['feedback_by_service'],
            'min_date': start_date,
            'max_date': end_date - timedelta(1)
        }))

        # Render template for patient feedback responses:
        tmpl = get_template('clinics/report_responses.html')
        response_html = tmpl.render(Context({
            'clinic': report.object,
            'response_stats': context['response_stats'],
        }))

        return {
            'num_registered': context['num_registered'],
            'num_started': context['num_started'],
            'perc_started': context['percent_started'],
            'num_completed': context['num_completed'],
            'perc_completed': context['percent_completed'],
            'fos_html': feedback_by_service_html,
            'feedback_stats': context['feedback_stats'],
            'feedback_clinics': context['feedback_clinics'],
            'responses_html': response_html,
            'max_chart_value': context['max_chart_value']
        }

    # def get_feedback_data(self, start_date, end_date, clinic):
    #    report = ClinicReport()
    #    report.object = clinic
    #
    #    report.start_date = start_date
    #    report.end_date = end_date
    #    report.curr_date = report.end_date
    #
    #    report.responses = SurveyQuestionResponse.objects.filter(
    #        clinic__id=report.object.id, datetime__gte=report.start_date,
    #        datetime__lte=report.end_date+timedelta(1))
    #
    #    report.questions = self.get_survey_questions(start_date, end_date)
    #    feedback_by_service = report.get_feedback_by_service()
    #
    #    # Calculate the Survey Participation Data via week filter
    #    visits = models.Visit.objects.filter(
    #        patient__clinic=clinic,
    #        survey_sent__isnull=False,
    #        visit_time__gte=start_date,
    #        visit_time__lt=(end_date + timedelta(1)))
    #    num_registered = visits.count()
    #    num_started = visits.filter(survey_started=True).count()
    #    num_completed = visits.filter(survey_completed=True).count()
    #
    #    if num_registered:
    #        percent_started = make_percentage(num_started, num_registered)
    #        percent_completed = make_percentage(num_completed, num_registered)
    #    else:
    #        percent_completed = None
    #        percent_started = None
    #
    #    # Calculate and render template for feedback on services
    #    tmpl = get_template('clinics/report_service.html')
    #    # questions = report.get_survey_questions(start_date, end_date)
    #    questions = report.questions
    #    cntxt = Context(
    #        {
    #            'feedback_by_service': feedback_by_service,
    #            'question_labels': [qtn.question_label for qtn in questions],
    #            'min_date': start_date,
    #            'max_date': end_date
    #        })
    #    html = tmpl.render(cntxt)
    #
    #    # Calculate feedback stats for chart
    #    lga_clinics = models.Clinic.objects.filter(lga=clinic.lga)
    #    chart_stats = report.get_feedback_statistics(
    #        lga_clinics, start_date=start_date, end_date=end_date)
    #    max_chart_value = max(chart_stats['sent'])
    #    chart_clinics = [clnc.name for clnc in lga_clinics]
    #    chart_clinics = self.format_chart_labels(chart_clinics, async=True)
    #
    #    # Calculate and render template for patient feedback responses
    #    response_tmpl = get_template('clinics/report_responses.html')
    #    other_clinics = lga_clinics.exclude(pk=clinic.pk)
    #    current_stats = report.get_response_statistics(
    #        (clinic, ), questions, start_date, end_date)
    #    other_stats = report.get_response_statistics(
    #        other_clinics, questions, start_date, end_date)
    #    try:
    #        margins = [(x[1] - y[1]) for x, y
    #                   in zip(current_stats, other_stats)]
    #    except TypeError:
    #        margins = [0] * len(current_stats)
    #    response_ctxt = Context(
    #        {
    #            'clinic': clinic,
    #            'response_stats': zip(questions, current_stats, other_stats, margins),
    #        })
    #    response_html = response_tmpl.render(response_ctxt)
    #
    #    return {
    #        'num_registered': num_registered,
    #        'num_started': num_started,
    #        'perc_started': percent_started,
    #        'num_completed': num_completed,
    #        'perc_completed': percent_completed,
    #        'fos_html': html,
    #        'feedback_stats': chart_stats,
    #        'feedback_clinics': chart_clinics,
    #        'responses_html': response_html,
    #        'max_chart_value': max_chart_value
    #    }

    def get(self, request, *args, **kwargs):
        start_date = get_date(request.GET['start_date']) if 'start_date' in request.GET else None
        end_date = (get_date(request.GET['end_date']) + timedelta(1)
                    ) if 'end_date' in request.GET else None
        clinic_id = request.GET.get('clinic_id')

        # Create an instance of a ClinicReport
        # clinic = models.Clinic.objects.get(id=clinic_id)

        # Collect the Comments filtered by the weeks
        # clinic_data = self.get_feedback_data(start_date, end_date, clinic)
        clinic_data = self.get_feedback_data(start_date, end_date, clinic_id)

        return HttpResponse(
            json.dumps(clinic_data, cls=DjangoJSONEncoder), content_type='text/json')


class LGAClinicsReport(DetailView):
    model = models.LGA

    def get_filename(self, start_date, end_date):
        filename = 'all-facilities'
        if start_date and end_date:
            filename = '%s (%s to %s)' % (
                filename,
                start_date.strftime('%d-%b-%Y'),
                (end_date - timedelta(1)).strftime('%d-%b-%Y'))
        return filename

    def render_facility_reports(self, start_date, end_date, out):
        elements = []
        renderer = pdf.ReportPdfRenderer()
        lga = self.get_object()
        # TODO: Please make me better Stan...PLEASE.
        for clinic in lga.clinic_set.all():
            report = ClinicReport()
            report.start_date = start_date
            report.end_date = end_date
            report.kwargs = {'pk': clinic.pk}
            report.object = report.get_object()
            context = report.get_context_data()
            elements.extend(renderer.render_to_list(context))
        renderer.render_to_response(elements, out)

    def get(self, request, *args, **kwargs):
        start_date = get_date(request.GET['start_date']) if 'start_date' in request.GET else None
        end_date = (get_date(request.GET['end_date']) + timedelta(1)
                    ) if 'end_date' in request.GET else None
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=%s.pdf' % (
            self.get_filename(start_date, end_date))
        self.render_facility_reports(start_date, end_date, response)
        return response


class LGAReport(ReportMixin, DetailView):
    template_name = 'clinics/summary.html'
    model = models.LGA

    def __init__(self, *args, **kwargs):
        super(LGAReport, self).__init__(*args, **kwargs)
        self.curr_date = None
        self.weeks = None

        if 'start_date' in kwargs and 'end_date' in kwargs:
            self.start_date = kwargs['start_date']
            self.end_date = kwargs['end_date']
        else:
            self.start_date = None
            self.end_date = None

    def get_object(self, queryset=None):
        obj = super(LGAReport, self).get_object(queryset)
        self.lga = obj
        self.responses = SurveyQuestionResponse.objects.filter(clinic__lga=obj)
        if self.start_date and self.end_date:
            self.responses = self.responses.filter(
                visit__visit_time__range=(self.start_date, self.end_date))
        self.responses = self.responses.select_related('question', 'service', 'visit')
        self.initialize_data()
        return obj

    def get_context_data(self, **kwargs):
        kwargs['responses'] = self.responses

        clinics = models.Clinic.objects.filter(lga=self.lga)
        kwargs['feedback_by_service'] = self.get_feedback_by_service()
        kwargs['feedback_by_clinic'] = self.get_feedback_by_clinic(clinics)
        kwargs['service_labels'] = [i.question_label for i in self.questions]
        kwargs['clinic_labels'] = self.get_clinic_labels()
        kwargs['question_labels'] = self.format_chart_labels(
            [qtn.question_label for qtn in self.questions])
        kwargs['lga'] = self.lga

        if self.responses:
            min_date = self.responses.aggregate(Min('datetime'))['datetime__min']
            kwargs['min_date'] = get_week_start(min_date)
            kwargs['max_date'] = timezone.now()
        else:
            kwargs['min_date'] = None
            kwargs['max_date'] = None

        # Patient feedback responses
        clinic_stats = self.get_response_statistics(
            clinics, self.questions)
        kwargs['response_stats'] = clinic_stats

        # Main comments
        kwargs['main_comments'] = self.get_main_comments(clinics)

        # Feedback stats for chart
        feedback_stats = self.get_feedback_statistics(clinics)
        kwargs['feedback_stats'] = feedback_stats
        kwargs['max_chart_value'] = max(feedback_stats['sent'])
        kwargs['feedback_clinics'] = self.format_chart_labels([cl.name for cl in clinics])

        kwargs['week_ranges'] = [
            (self.start_day(start), self.start_day(end)) for start, end in
            self.get_week_ranges(kwargs['min_date'], kwargs['max_date'])]
        kwargs['week_start'], kwargs['week_end'] = self.get_current_week()
        data = super(LGAReport, self).get_context_data(**kwargs)
        return data


class LGAReportAjax(View):

    def get_data(self, start_date, end_date, lga):
        clinics = models.Clinic.objects.filter(lga=lga)
        report = ReportMixin()
        report.responses = SurveyQuestionResponse.objects.filter(
            visit__visit_time__range=(start_date, end_date),
            clinic__in=clinics)
        report.initialize_data()
        report.questions = report.get_survey_questions(start_date, end_date)

        service_feedback = report.get_feedback_by_service()
        clinic_feedback = report.get_feedback_by_clinic(clinics, start_date, end_date)
        question_labels = report.format_chart_labels(
            [qtn.question_label for qtn in report.questions], async=True)

        # Render html templates
        data = {
            'feedback_by_service': service_feedback,
            'feedback_by_clinic': clinic_feedback,
            'min_date': start_date,
            'max_date': end_date,
            'service_labels': question_labels,
            'clinic_labels': report.get_clinic_labels(),
        }
        service_tmpl = get_template('clinics/by_service.html')
        context = Context(data)
        service_html = service_tmpl.render(context)

        clinic_tmpl = get_template('clinics/by_clinic.html')
        clinic_html = clinic_tmpl.render(context)

        # Calculate stats for feedback chart
        chart_stats = report.get_feedback_statistics(
            clinics, start_date=start_date, end_date=end_date)
        max_chart_value = max(chart_stats['sent'])

        # Calculate and render template for patient feedback responses
        response_stats = report.get_response_statistics(
            clinics, report.questions, start_date, end_date)

        return {
            'facilities_html': clinic_html,
            'services_html': service_html,
            'feedback_stats': chart_stats,
            'feedback_clinics': report.format_chart_labels(clinics, async=True),
            'response_stats': [i[1] for i in response_stats],
            'question_labels': report.format_chart_labels(question_labels, async=True),
            'max_chart_value': max_chart_value,
        }

    def get(self, request, *args, **kwargs):

        _start_date = request.GET.get('start_date')
        _end_date = request.GET.get('end_date')
        _lga = request.GET.get('lga')

        if not all((_start_date, _end_date, _lga)):
            return HttpResponseBadRequest('')

        start_date = get_date(_start_date)
        end_date = get_date(_end_date)
        try:
            lga = models.LGA.objects.get(pk=_lga)
        except models.LGA.DoesNotExist:
            return HttpResponseBadRequest('Wrong LGA')

        data = self.get_data(start_date, end_date, lga)
        json_data = json.dumps(data, cls=DjangoJSONEncoder)

        return HttpResponse(json_data, content_type='text/json')


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
