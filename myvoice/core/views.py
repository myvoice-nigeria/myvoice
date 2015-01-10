from django.db.models import Count
from django.views.generic import TemplateView
from myvoice.clinics.models import Clinic, Patient, Visit
from collections import Counter


class Home(TemplateView):
    template_name = 'core/home.html'

    def get_facility_counts(self):
        """Returns the total count of facilities, grouped by type, and the count of LGAs."""
        lgas = set()
        counts = Counter()
        for row in Clinic.objects.values('lga', 'type').annotate(facilities=Count('id')):
            lgas.add(row['lga'])
            counts[row['type']] += row['facilities']
        counts['lga'] = len(lgas)
        return counts

    def get_progress_to_date(self):
        """Returns a dictionary used to populate the "Progress to Date" view on the home page."""
        # Assumption: since patients are registered by clinic staff, the number of unique senders
        #  in the Visit table, should be roughly equal to the number of staff. I'm doing this,
        #  'cause presently there's no data in the ClinicStaff table.
        staff = Visit.objects.values('sender').distinct()
        sent = Visit.objects.values('mobile').distinct()
        started = Visit.objects.filter(mobile__in=sent, survey_started=True)
        facility_counts = self.get_facility_counts()
        return {'staff_count': staff.count(),
                'primary_facilities_count': facility_counts['primary'],
                'general_hospitals_count': facility_counts['general'],
                'lga_count': facility_counts['lga'],
                'patient_count': Patient.objects.count(),
                'survey_sent_count': sent.count(),
                'survey_started_count': started.count()}
