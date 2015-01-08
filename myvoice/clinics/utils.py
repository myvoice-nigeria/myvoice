from myvoice.clinics.models import Visit
from itertools import groupby


def groupbylist(*args, **kwargs):
    return [(k, list(g)) for k, g in groupby(*args, **kwargs)]


def group_facilities(facilities):
    """
    Groups an iterable of Facilities, first by State, then by LGA.
    
    Note that we assume the list is already sorted.
    """
    by_lga = groupbylist(facilities, lambda x: x.lga)
    by_state = groupbylist(by_lga, lambda x: x[0].state)
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
