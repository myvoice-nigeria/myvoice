from django.core.management.base import BaseCommand

from ... import importer


class Command(BaseCommand):

    def handle(self, flow_id, **options):
        importer.import_responses(flow_id)
