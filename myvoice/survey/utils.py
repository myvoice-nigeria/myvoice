from collections import Counter
from itertools import groupby
from operator import attrgetter, itemgetter

from myvoice.core.utils import make_percentage


# Labels of questions which must be answered to complete a survey.
REQUIRED_QUESTIONS = ['Open Facility', 'Respectful Staff Treatment',
                      'Clean Hospital Materials', 'Charged Fairly',
                      'Wait Time']


def analyze(responses, answer):
    """
    Returns the percentage (out of 100) of responses with the given answer, or
    None if there are no responses.
    """
    if responses:
        count = len([r for r in responses if r.response == answer])
        return make_percentage(count, len(responses))
    return None


def get_mode(responses):
    """Returns the most commonly-reported answer, or None if there are no responses."""
    answers = [r.response for r in responses if r.response]
    if answers:
        return max(Counter(answers).iteritems(), key=itemgetter(1))[0]
    return None


def group_responses(responses, ordering, grouping=None):
    """Returns a grouped list of responses.

    responses should use prefetch_related or select_related with the
    given attributes for the best performance.
    """
    if grouping is None:
        grouping = ordering
    ordered = [r for r in sorted(responses, key=attrgetter(ordering))]
    return [(l, list(r)) for l, r in groupby(ordered, key=attrgetter(grouping))]


def convert_to_local_format(phone):
    """Simplistic utility to convert phone number to local Nigerian format."""
    if phone.startswith('0') and len(phone) == 11:
        return phone  # Aleady in the correct format.
    elif phone.startswith('+234') and len(phone) == 14:
        return '0' + phone[4:]
    elif phone.startswith('234') and len(phone) == 13:
        return '0' + phone[3:]
    raise Exception("Unable to understand {0}".format(phone))


def convert_to_international_format(phone):
    """Simplistic utility to convert phone number to international format."""
    if phone.startswith('+234') and len(phone) == 14:
        return phone
    elif phone.startswith('234') and len(phone) == 13:
        return '+' + phone
    elif phone.startswith('0') and len(phone) == 11:
        return '+234' + phone[1:]
    raise Exception("Unable to convert {0}".format(phone))


def get_detailed_comments(responses):
    """Returns all responses which are open-ended.

    Ordered by question, in order to use {% regroup %} in a template.
    """
    from .models import SurveyQuestion
    open_ended = responses.filter(question__question_type=SurveyQuestion.OPEN_ENDED)
    return open_ended.order_by('question', 'datetime')


def get_completion_count(responses):
    """Returns the count of responses which are completed.

    Assumes that responses all belong to the same survey.
    """
    by_visit = group_responses(responses, 'visit.id')
    results = [[r.question.label for r in list(rlist)] for _, rlist in by_visit]
    return len([r for r in results if all([l in r for l in REQUIRED_QUESTIONS])])


def get_registration_count(clinic):
    """Returns the count of patients who should have received this survey."""
    from myvoice.clinics.models import Visit
    return Visit.objects.filter(patient__clinic=clinic).count()
