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
        visits = Visit.objects.all()
        visits.update(survey_sent=None)  # Reset all survey start times.
        eta = _get_survey_start_time()
        for visit in visits:
            start_feedback_survey.apply_async(args=[visit.pk], eta=eta)
            logger.debug("Rescheduled survey to start for visit {} "
                         "at {}.".format(visit.pk, eta))
