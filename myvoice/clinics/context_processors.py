from myvoice.clinics.models import Clinic
from myvoice.clinics.utils import group_facilities


def facilities(request):
    # Need to sort first, since we'll be grouping later:
    all_facilities = Clinic.objects.order_by('lga__state', 'name').prefetch_related('lga__state')
    grouped = group_facilities(all_facilities)
    
    return {
        'all_facilities': all_facilities,
        'grouped_facilities': grouped,
    }
