import logging

from django.core.management.base import BaseCommand

from myvoice.clinics.models import Visit

from ...tasks import start_feedback_survey, _get_survey_start_time


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    One-time-use command to restart survey for all visits.

    Even though we marked each Visit as having the survey sent, an error
    prevented the surveys from actually being sent.
    """

    def handle(self, *args, **kwargs):
        # Only include visits for which we've already tried to send a
        # survey (all others should be fine).
        visits = Visit.objects.filter(survey_sent__isnull=False)

        eta = _get_survey_start_time()
        for visit in visits:
            start_feedback_survey.apply_async(args=[visit.pk], eta=eta)
            logger.debug("Rescheduled survey to start for visit {} "
                         "at {}.".format(visit.pk, eta))

        # Reset all survey start times.
        # Must be done at the end to avoid accidentally grabbing
        # surveys we originally excluded when re-fetching the query.
        visits.update(survey_sent=None)
