from celery.task import task

from . import importer
from .models import Survey


@task
def import_responses():
    """Periodically check for new responses for each survey."""
    for survey in Survey.objects.active():
        importer.import_responses(survey.flow_id)
