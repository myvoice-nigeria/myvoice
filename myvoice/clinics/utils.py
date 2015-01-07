from myvoice.clinics.models import Visit
from itertools import groupby

def group_facilities(clinics):
    """
    Groups an iterable of Clinics, first by State, then by LGA.
    
    Note that we assume the list is already sorted.
    """
    by_lga = groupby(clinics, lambda c: c.lga)
    by_state = groupby(by_lga, lambda g: g[0].state)
    return by_state

def get_triggered_count(a_clinic="", service="", start_date="", end_date=""):
    st_query = Visit.objects.filter(survey_sent__isnull=False)
    if a_clinic:
        st_query = st_query.filter(patient__clinic=a_clinic)
    if start_date:
        st_query = st_query.filter(visit_time__gte=start_date)
    if end_date:
        st_query = st_query.filter(visit_time__lte=end_date)
    if service:
        st_query = st_query.filter(service__name=service)
    return st_query.count()
