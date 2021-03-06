import logging

import dateutil.parser

from myvoice.clinics.models import Visit

from . import utils as survey_utils
from .models import Survey, SurveyQuestion, SurveyQuestionResponse
from .textit import TextItApi


logger = logging.getLogger(__file__)


def import_survey(flow_id, role=None):
    """
    Imports questions for a TextIt flow, overwriting any questions (and
    responses) that currently exist.

    Per Nic Pottier:

        "The flow definitions aren't part of the API just yet as we haven't
        settled on standardizing their format. (things are just changing too
        quickly) ... You may find downloading the definition through the
        export functionality gets you what you need ... though we can't
        guarantee that it will be completely stable in the short term."

    So this works, for now.

    TODO: Try to update existing data, so that we can make changes without
    deleting responses unnecessarily.
    """

    def _guess_type_and_categories(question):
        """
        This is just (educated) guesswork. Per Nic Pottier, TextIt is not yet
        exposing the question type because the API is very unstable.

        NOTE: This only handles open-ended and multiple choice questions,
        as we don't currently have any range questions to deal with.
        """
        categories = [r['category'] for r in question['rules']]
        if len(categories) == 1:
            # Things that are labeled open-ended on the TextIt side have just one
            # category that is always called 'All Responses'.
            if categories[0] == 'All Responses':
                return SurveyQuestion.OPEN_ENDED, ""
        if len(categories) == 2:
            # Unfortunately some open-ended questions are registered as
            # multiple-choice on TextIt so that the 'STOP' keyword can be used.
            # Typically they have a 'Stop' and an 'Other' category.
            normalized = [c.lower() for c in categories]
            if 'stop' in normalized:
                if 'other' in normalized:
                    return SurveyQuestion.OPEN_ENDED, ""

        # We'll handle STOP and OTHER responses as special cases.
        categories = [c for c in categories if c.lower() not in ('stop', 'other')]
        return SurveyQuestion.MULTIPLE_CHOICE, "\n".join(categories)

    def _guess_question_text(question_id, action_sets):
        """
        The questions themselves aren't directly associated with the rules.
        We have to guess at what the best question would be, from the actions
        (in this case, the text message prompts) that get the user to that
        question node. This isn't the most reliable method so this field
        should remain editable in the database to allow admins to fix up any
        mistakes we made.
        """
        possible_questions = [action['msg']
                              for action_set in action_sets
                              for action in action_set['actions']
                              if action_set['destination'] == question_id and
                              action['type'] == 'reply']
        if possible_questions:
            q = possible_questions[0]
            if '?' in q:
                # Get the first sentence that ends in a question mark.
                # Many 'questions' also include directives like
                # "Reply to 55999" at the end.
                return q[:q.index('?') + 1]
            return q
        return ''

    data = TextItApi().get_flow_export(flow_id)
    flow = data['flows'][0]  # Seems only 1 is returned.
    rules = flow['definition']['rule_sets']
    survey, _ = Survey.objects.get_or_create(flow_id=flow['id'])
    survey.name = flow['name']
    if role is not None:
        survey.role = role
    survey.save()
    survey.surveyquestion_set.all().delete()
    for question in rules:
        label = question['label']
        question_id = question['uuid']
        question_text = _guess_question_text(question_id, flow['definition']['action_sets'])
        question_type, categories = _guess_type_and_categories(question)
        SurveyQuestion.objects.create(
            survey=survey,
            question_id=question_id,
            question=question_text,
            label=label,
            question_type=question_type,
            categories=categories,
        )
    return survey


def import_responses(flow_id):
    """
    Retrieves all runs through the flow with the given ID, and stores each
    value in the run as a SurveyQuestionResponse object.

    Existing responses will only be overwritten if there is a more recent
    value.
    """
    try:
        survey = Survey.objects.get(flow_id=flow_id)
    except Survey.DoesNotExist:
        raise Exception("There is no survey for flow_id {0}".format(flow_id))

    questions = dict([(q.label, q) for q in survey.surveyquestion_set.all()])

    runs = TextItApi().get_runs_for_flow(flow_id)
    for rrun in runs:
        # A run through a flow can have anywhere from 0 to N answers, where N
        # is the number of questions associated with the survey.
        for answer in rrun['values']:
            label = answer['label']
            local_phone = survey_utils.convert_to_local_format(rrun['phone'])
            response_time = dateutil.parser.parse(answer['time'])

            # Only process answers for questions we know about.
            if label not in questions:
                kwargs = {'flow_id': flow_id, 'label': label}
                logger.error("Received answer to unknown question in "
                             "flow {flow_id}: {label}".format(**kwargs))
                continue

            # Discard 'stop' and 'error' answers.
            if answer['category'].lower() in ('stop', 'error'):
                logger.debug("Discarding message that user used to stop "
                             "the survey.")
                continue

            # Find visits we've registered for this phone number that
            # were registered before this response was received.
            visits = Visit.objects.filter(mobile=local_phone)
            visits = visits.filter(visit_time__lte=response_time)
            visits = visits.order_by('-visit_time')
            try:
                # Choose the visit closest in time to this response.
                visit = visits[0]
            except IndexError:
                logger.debug("Discarding answer because we cannot determine "
                             "which visit it should be associated with.")
                continue

            # Determine whether we've seen this response before (or another
            # response to the same question).
            try:
                response = SurveyQuestionResponse.objects.get(
                    visit=visit, question=questions.get(label))
            except SurveyQuestionResponse.DoesNotExist:
                # Create a new object - this is the first answer we've seen to
                # this question.
                response = SurveyQuestionResponse(
                    visit=visit, question=questions.get(label))
            else:
                # The user has already answered this question. Either we've
                # imported this answer before, or the user has answered the
                # question more than once (as would happen if the user gives
                # an unintelligible answer and the question is re-asked).
                # We'll keep the most recent answer.
                if response_time <= response.datetime:
                    logger.debug("Discarding answer because we have a more "
                                 "recent answer to the same question already "
                                 "in the database.")
                    continue

            if answer['category'].lower() in ('other', 'all responses'):
                # 'category' is the normalized answer to this question.
                # Most often 'other' and 'all responses' signify that this
                # is an open-ended question, but it is used with multiple
                # choice questions too. Either way, the raw answer will be
                # much more useful than the normalized answer.
                value = answer['value']
            else:
                value = answer['category']  # Normalized response.

            response.response = value
            response.datetime = response_time

            try:
                response.save()
            except:  # Blanket exception in case anything goes wrong.
                msg_args = (local_phone, rrun['run'], answer)
                msg = "Unable to save response from {} in run {}: {}"
                logger.exception(msg.format(*msg_args))
