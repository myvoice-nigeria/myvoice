import datetime
import logging

from celery.task import task

from myvoice.clinics.models import Visit

from . import importer, utils as survey_utils
from .models import Survey
from .textit import TextItApi


logger = logging.getLogger(__name__)


@task
def import_responses():
    """Periodically check for new responses for each survey."""
    for survey in Survey.objects.active():
        importer.import_responses(survey.flow_id)

@task
def start_surveys():
    """Initiate the feedback survey for recent visits."""
    try:
        survey = Survey.objects.get(role=Survey.PATIENT_FEEDBACK)
    except Survey.DoesNotExist:
        logger.error("No patient feedback survey is registered.")
        return

    # Only send a survey if it hasn't been sent before.
    visits = Visit.objects.filter(survey_sent=False)

    # Wait at least one hour from the visit registration time.
    max_visit_time = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    visits = visits.filter(visit_time__lte=max_visit_time)

    # Grab the phone numbers of all patients from applicable visits.
    phones = list(set(visits.values_list('patient__mobile', flat=True)))
    phones = [survey_utils.convert_to_international_format(p) for p in phones]

    try:
        TextItApi().start_flow(survey.flow_id, phones)
    except:
        logger.exception("Error sending surveys to users.")
    else:
        visits.update(survey_sent=True)
