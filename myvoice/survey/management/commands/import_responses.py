from django.core.management.base import BaseCommand, CommandError

from ... import importer


class Command(BaseCommand):

    def handle(self, *args, **options):
        for clinic_id in args:
            importer.import_responses(clinic_id)
