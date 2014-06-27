from django.core.management.base import BaseCommand

from ... import importer


class Command(BaseCommand):

    def handle(self, flow_id, role=None, **options):
        importer.import_survey(flow_id, role)
