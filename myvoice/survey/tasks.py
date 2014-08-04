import logging

from celery.task import task

from django.conf import settings
from django.utils import timezone

from myvoice.clinics.models import Visit

from . import importer, utils as survey_utils
from .models import Survey
from .textit import TextItApi, TextItException


logger = logging.getLogger(__name__)


def _get_survey_start_time(tm):
    # Schedule the survey to be sent in the future.
    eta = tm + settings.DEFAULT_SURVEY_DELAY
    earliest, latest = settings.SURVEY_TIME_WINDOW
    if eta.hour > latest:  # It's too late in the day - send tomorrow.
        eta = eta + timezone.timedelta(days=1)
        eta = eta.replace(hour=earliest, minute=0, second=0, microsecond=0)
    elif eta.hour < earliest:  # It's too early in the day - send later.
        eta = eta.replace(hour=earliest, minute=0, second=0, microsecond=0)
    return eta


@task
def import_responses():
    """Periodically check for new responses for each survey."""
    logger.debug('Importing responses from active surveys.')
    for survey in Survey.objects.active():
        logger.debug('Starting to import responses for flow {0}.'.format(survey.flow_id))
        importer.import_responses(survey.flow_id)
        logger.debug('Finished importing responses for flow {0}.'.format(survey.flow_id))


@task
def start_feedback_survey(visit_pk):
    """Initiate the patient feedback survey for a Visit."""
    try:
        survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
    except Survey.DoesNotExist:
        logger.exception("No patient feedback survey is registered.")
        raise

    try:
        visit = Visit.objects.get(pk=visit_pk)
    except Visit.DoesNotExist:
        logger.exception("Unable to find visit with pk {}.".format(visit_pk))
        raise

    if visit.survey_sent is not None:
        logger.warning("Survey has already been sent for visit {}.".format(visit_pk))
        return

    try:
        TextItApi().start_flow(survey.flow_id, visit.mobile)
    except TextItException:
        logger.exception("Error sending survey for visit {}.".format(visit.pk))
        raise
    else:
        visit.survey_sent = timezone.now()
        visit.save()
        logger.debug("Initiated survey for visit {} "
                     "at {}.".format(visit.pk, visit.survey_sent))


@task
def handle_new_visits():
    """
    Schedule when feedback survey should start for all new visitors.
    Except for blocked visitors.
    """
    blocked = Visit.objects.exclude(sender='').values_list('sender', flat=True).distinct()
    try:
        # Look for visits for which we haven't sent surveys.
        # We use welcome_sent to show that we have not scheduled surveys
        # We can't use survey_sent because they are async and we may experience
        # overlaps.
        visits = Visit.objects.filter(welcome_sent__isnull=True,
                                      mobile__isnull=False).exclude(mobile__in=blocked)

        # Grab the phone numbers of all patients from applicable visits.
        new_visits = []
        phones = []
        for visit in visits:
            # Only schedule the survey to be started if the phone number
            # can be converted to valid international format.
            international = survey_utils.convert_to_international_format(visit.mobile)
            if international:
                new_visits.append(visit)
                phones.append(international)
            else:
                logger.debug("Unable to send welcome message to "
                             "visit {}.".format(visit.pk))

        if not new_visits:
            # Don't bother continuing if there aren't any new visits.
            return

        # Schedule when to initiate the flow.
        eta = _get_survey_start_time(timezone.now())
        for visit in new_visits:
            if visit.survey_sent is not None:
                logger.debug("Somehow a survey has already been sent for "
                             "visit {}.".format(visit.pk))
                continue
            start_feedback_survey.apply_async(args=[visit.pk], eta=eta)
            logger.debug("Scheduled survey to start for visit "
                         "{} at {}.".format(visit.pk, eta))

        # update visits at the end, since adding a value for welcome_sent prevents
        # us from finding the values we were originally interested in
        welcomed_ids = [v.pk for v in new_visits]
        # We update welcome_sent even though we don't send any welcome msg.
        Visit.objects.filter(pk__in=welcomed_ids).update(welcome_sent=timezone.now())
    except:
        logger.exception("Encountered unexpected error while handling new visits.")
        raise
