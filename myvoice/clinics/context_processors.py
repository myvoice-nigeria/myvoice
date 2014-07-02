from myvoice.clinics.models import Clinic


def facilities(request):
    return {
        'all_facilities': Clinic.objects.order_by('name'),
    }
