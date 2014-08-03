import datetime
from dateutil.parser import parse
from django.utils import timezone


def get_week_start(date):
    """Returns midnight of the Monday prior to the given date."""
    days_since_monday = date.weekday()
    monday = date - timezone.timedelta(days=days_since_monday)
    monday = monday.replace(microsecond=0, second=0, minute=0, hour=0)
    return monday


def get_week_end(date):
    """Returns the last microsecond of the Sunday after the given date."""
    return get_week_start(date) + timezone.timedelta(days=7, microseconds=-1)


def make_percentage(numerator, denominator, places=0):
    """Returns a percentage out of 100 to the number of places given."""
    percentage = float(numerator) / float(denominator)
    return round(percentage * 100, places)


def extract_attr(obj, name):
    parts = name.split('.')
    # Not likely
    if not name:
        return None
    if len(parts) == 1:
        attr = getattr(obj, name)
        return attr() if callable(attr) else attr
    else:
        newobj = getattr(obj, parts[0])
        if callable(newobj):
            newobj = newobj()
        return extract_attr(newobj, '.'.join(parts[1:]))


def extract_qset_data(qset, fld_names):
    """Extract data of fields in fld_names from queryset to a list."""
    out = [[header.replace('.', ' ') for header in fld_names]]
    for obj in qset:
        line = [str(extract_attr(obj, fld_name)).decode('utf-8', 'ignore')
                for fld_name in fld_names]
        out.append(line)
    return out


def daterange(start_date, end_date):
    """Yield dates between start_date and end_date inclusive."""
    for n in range(int((end_date - start_date).days + 1)):
        yield start_date + datetime.timedelta(n)


def get_date(the_date=None):
    if the_date:
        if isinstance(the_date, datetime.datetime):
            return the_date
        elif isinstance(the_date, basestring):
            return parse(the_date)
    return None
