import datetime
from dateutil.parser import parse
from django.utils import timezone
import datetime
from dateutil.parser import parse


def hour_to_hr(txt):
    return txt.replace('hour', 'hr')


def get_week_start(date):
    """Returns midnight of the Monday prior to the given date."""

    if date:
        days_since_monday = date.weekday()
    else:
        return None
    monday = date - timezone.timedelta(days=days_since_monday)
    monday = monday.replace(microsecond=0, second=0, minute=0, hour=0)
    return monday


def get_week_end(date):
    """Returns the last microsecond of the Sunday after the given date."""
    if date:
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


def get_date(the_date):
    if the_date and isinstance(the_date, basestring):
        return timezone.make_aware(parse(the_date), timezone.utc)


def calculate_weeks_ranges(start_date, end_date):
    """Returns a list of tuples of dates between self.start_date and self.end_date"""

    today = datetime.datetime.now()
    if not start_date:
        # Lauren said this date was an ok date to start - this is due to Zalli having no data.
        start_date = parse("2014-07-01")
    if not end_date:
        end_date = today

    curr_week_start = get_week_start(today)
    curr_week_end = get_week_end(today)
    if curr_week_end > today:
        date_diff = (curr_week_end.date() - today.date()).days
        curr_week_start = curr_week_start - datetime.timedelta(date_diff)
        curr_week_end = curr_week_end - datetime.timedelta(date_diff)

    week_list = [{"start": start_date, "end": end_date}]
    week_list.append({"start": curr_week_start, "end": curr_week_end})
    start_date = get_week_start(start_date)

    next_monday = start_date
    while(next_monday < end_date):
        next_monday = start_date + datetime.timedelta(days=0, weeks=1)
        week_list.append({"start": start_date,
                          "end": next_monday - datetime.timedelta(days=1, weeks=0)})
        start_date = next_monday
    return week_list
