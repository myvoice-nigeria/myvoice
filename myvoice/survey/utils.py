from collections import Counter
from itertools import groupby
import logging
from operator import attrgetter, itemgetter

from dateutil.parser import parse

from myvoice.core.utils import make_percentage
from myvoice.survey.models import SurveyQuestionResponse
from myvoice.clinics.models import Clinic, Service


logger = logging.getLogger(__name__)

# Labels of questions which must be answered to complete a survey.
REQUIRED_QUESTIONS = ['Open Facility', 'Respectful Staff Treatment',
                      'Clean Hospital Materials', 'Charged Fairly',
                      'Wait Time']


def analyze(answers, correct_answer):
    """
    Returns the percentage (out of 100) of responses with the given answer, or
    None if there are no responses.
    """
    if answers:
        count = len([r for r in answers if r == correct_answer])
        return make_percentage(count, len(answers))
    return None


def get_mode(answers, acceptable_answers=None):
    """Returns the most commonly-reported answer, or None if there are no responses."""
    if acceptable_answers is not None:
        answers = [a for a in answers if a in acceptable_answers]
    if answers:
        mode = max(Counter(answers).iteritems(), key=itemgetter(1))[0]
        return mode.replace('hour', 'hr')
    return None


def group_responses(responses, ordering, grouping=None, keyfunc=attrgetter):
    """Returns a grouped list of responses.

    responses should use prefetch_related or select_related with the
    given attributes for the best performance.
    For a ValuesQueryset use keyfunc=itemgetter.
    """
    if grouping is None:
        grouping = ordering
    ordered = [r for r in sorted(responses, key=keyfunc(ordering))]
    return [(l, list(r)) for l, r in groupby(ordered, key=keyfunc(grouping))]


def convert_to_local_format(phone):
    """Simplistic utility to convert phone number to local Nigerian format."""
    if phone.startswith('0') and len(phone) == 11:
        return phone  # Already in the correct format.
    elif phone.startswith('+234') and len(phone) == 14:
        return '0' + phone[4:]
    elif phone.startswith('234') and len(phone) == 13:
        return '0' + phone[3:]
    else:
        logger.warning("Unable to convert {} to Nigerian format.".format(phone))
        return None


def convert_to_international_format(phone):
    """Simplistic utility to convert phone number to international format."""
    if phone.startswith('+234') and len(phone) == 14:
        return phone
    elif phone.startswith('234') and len(phone) == 13:
        return '+' + phone
    elif phone.startswith('0') and len(phone) == 11:
        return '+234' + phone[1:]
    else:
        logger.warning("Unable to convert {} to international format.".format(phone))
        return None


def filter_sqr_query(responses, clinic="", service="", start_date="", end_date=""):
    """Returns the query of survey question responses which are completed, based on filters"""
    if clinic:
        if isinstance(clinic, str) or isinstance(clinic, unicode):
            clinic = Clinic.objects.get(name__iexact=clinic)
        responses = responses.filter(clinic=clinic)

    if service:
        if isinstance(service, str) or isinstance(service, unicode):
            service = Service.objects.get(name__iexact=service)
        responses = responses.filter(service=service)

    if start_date:
        if isinstance(start_date, str) or isinstance(start_date, unicode):
            start_date = parse(start_date)
        responses = responses.filter(visit__visit_time__gte=start_date)

    if end_date:
        if isinstance(end_date, str) or isinstance(end_date, unicode):
            end_date = parse(end_date)
        responses = responses.filter(visit__visit_time__lte=end_date)

    return responses


def get_completion_count(responses):
    """Returns the count of responses which are completed.

    Assumes that responses all belong to the same survey.
    """
    by_visit = group_responses(responses, 'visit.id')
    results = [[r.question.label for r in list(rlist)] for _, rlist in by_visit]
    return len([r for r in results if all([l in r for l in REQUIRED_QUESTIONS])])


def get_completion_query(responses="", clinic="", service="", start_date="", end_date=""):
    if not responses:
        responses = SurveyQuestionResponse.objects.all()
    return filter_sqr_query(responses.filter(
        question__label="Wait Time"), clinic, service, start_date, end_date)


def get_completion_qcount(responses="", clinic="", service="", start_date="", end_date=""):
    return get_completion_query(responses, clinic, service, start_date, end_date).count()


def get_registration_count(clinic):
    """Returns the count of patients who should have received this survey."""
    from myvoice.clinics.models import Visit
    return Visit.objects.filter(survey_sent__isnull=False, patient__clinic=clinic).count()


def get_started_query(responses="", clinic="", service="", start_date="", end_date=""):
    if not responses:
        responses = SurveyQuestionResponse.objects.all()
    return filter_sqr_query(responses.filter(question__label__iexact="Open Facility")
                            .filter(question__question_type__iexact="multiple-choice"),
                            clinic, service, start_date, end_date)


def get_started_count(responses, clinic="", service="", start_date="", end_date=""):
    """Returns the count of responses which are started."""
    return get_started_query(responses, clinic, service, start_date, end_date).count()


def display_feedback(response_text):
    """Returns whether or not the text response should be displayed."""
    if not response_text or len(response_text.strip()) <= 1:
        return False
    if response_text.strip().lower() in ['55999', 'yes', 'no', 'n0', 'start']:
        return False
    return True
