from collections import defaultdict, Counter
from itertools import groupby
from operator import attrgetter, itemgetter


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
