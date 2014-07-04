from collections import defaultdict, Counter
from operator import itemgetter


def analyze(responses, answer):
    """
    Return the percentage (out of 100) of responses with the given answer, or
    None if there are no responses.
    """
    if responses:
        count = len([r for r in responses if r.response == answer])
        return int(float(count) / len(responses) * 100)


def get_mode(responses):
    """Returns the most commonly-reported answer, or None if there are no responses."""
    answers = [r.response for r in responses if r.response]
    if answers:
        return max(Counter(answers).iteritems(), key=itemgetter(1))[0]
    return None


def group_by_question(responses):
    """Return a dictionary of question labels to associated responses.

    responses should use .prefetch('question') or .select_related('question')
    for fastest results.
    """
    # FIXME - unsure why this isn't working for Feedback by Week.
    # return dict([(l, list(r)) for l, r in groupby(responses, key=attrgetter('question.label'))])
    grouped = defaultdict(list)
    for r in responses:
        grouped[r.question.label].append(r)
    return grouped


def convert_to_local_format(phone):
    """Simplistic utility to convert phone number to local Nigerian format."""
    if phone.startswith('0'):
        if len(phone) == 11:
            return phone  # Aleady in the correct format.
    elif phone.startswith('+234'):
        new_phone = '0' + phone[4:]
        if len(new_phone) == 11:
            return new_phone
    elif phone.startswith('234'):
        new_phone = '0' + phone[3:]
        if len(new_phone) == 11:
            return new_phone
    raise Exception("Unable to understand {0}".format(phone))
