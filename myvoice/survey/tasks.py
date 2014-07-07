import datetime
import logging

from celery.task import task

from django.utils import timezone

from myvoice.clinics.models import Visit

from . import importer, utils as survey_utils
from .models import Survey
from .textit import TextItApi, TextItException


logger = logging.getLogger(__name__)


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
        return

    try:
        visit = Visit.objects.get(pk=visit_pk)
    except Visit.DoesNotExist:
        logger.exception("Unable to find visit with pk {}.".format(visit_pk))
        return

    if visit.survey_sent is not None:
        logger.debug("Survey has already been sent for visit {}.".format(visit_pk))
        return

    try:
        TextItApi().start_flow(survey.flow_id, visit.mobile)
    except TextItException:
        logger.exception("Error sending survey for visit {}.".format(visit.pk))
    else:
        visit.survey_sent = timezone.now()
        visit.save()
        logger.debug("Initiated survey for visit {} "
                     "at {}.".format(visit.pk, visit.survey_sent))


@task
def handle_new_visits():
    """
    Sends a welcome message to all new visitors and schedules when to start
    the feedback survey.
    """
    try:
        # Look for visits for which we haven't sent a welcome message.
        visits = Visit.objects.filter(welcome_sent__isnull=True,
                                      mobile__isnull=False)
        # Don't bother continuing if there aren't any new visits
        if not visits.exists():
            return

        # Send a "welcome" message immediately.
        # Grab the phone numbers of all patients from applicable visits.
        welcomed_visits = []
        phones = []
        for visit in visits:
            # Only send a welcome message and schedule the survey to be started if
            # the phone number can be converted to valid international format.
            international = survey_utils.convert_to_international_format(visit.mobile)
            if international:
                welcomed_visits.append(visit)
                phones.append(international)
            else:
                logger.debug("Unable to send welcome message to "
                             "visit {}.".format(visit.pk))
        try:
            welcome_message = ("Hi, thank you for your visit to the hospital. "
                               "We care about your health. Help us make this "
                               "hospital better. Please reply to the texts we "
                               "will send you shortly.")
            TextItApi().send_message(welcome_message, phones)
        except TextItException:
            logger.exception("Error sending welcome message to {}".format(phones))
            # re-raise the exception so Celery knows the task failed
            raise

        # Schedule when to initiate the flow.
        # Only schedule flows for visits which we were able to welcome.
        now = timezone.now()  # UTC
        for visit in welcomed_visits:
            if visit.survey_sent is not None:
                logger.debug("Somehow a survey has already been sent for "
                             "visit {} even though we hadn't sent the welcome "
                             "message.".format(visit.pk))
                continue

            # Schedule the survey to be sent 3 hours later.
            eta = now + datetime.timedelta(hours=3)
            if eta.hour > 20:
                # It's past 8pm UTC / 9pm WAT. Send tomorrow morning at 8am WAT.
                eta = eta.replace(day=now.day + 1, hour=7, minute=0, second=0,
                                  microsecond=0)
            elif eta.hour < 7:
                # It's before 7am UTC / 8am WAT. Send at 8am WAT.
                eta = eta.replace(hour=7, minute=0, second=0, microsecond=0)
            start_feedback_survey.apply_async(args=[visit.pk], eta=eta)
            logger.debug("Scheduled survey to start for visit "
                         "{} at {}.".format(visit.pk, eta))

        # update visits at the end, since adding a value for welcome_sent prevents
        # us from finding the values we were originally interested in
        welcomed_ids = [v.pk for v in welcomed_visits]
        Visit.objects.filter(pk__in=welcomed_ids).update(welcome_sent=timezone.now())
    except Exception as e:
        logger.exception("Encountered unexpected error while handling new visits.")
        raise
