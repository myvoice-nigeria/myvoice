import datetime


def get_week_start(date):
    """Returns midnight of the Monday prior to the given date."""
    days_since_monday = date.weekday()
    monday = date - datetime.timedelta(days=days_since_monday)
    monday = monday.replace(microsecond=0, second=0, minute=0, hour=0)
    return monday


def get_week_end(date):
    """Returns the last microsecond of the Sunday after the given date."""
    return get_week_start(date) + datetime.timedelta(days=7, microseconds=-1)


def make_percentage(numerator, denominator, places=0):
    """Returns a percentage out of 100 to the number of places given."""
    percentage = float(numerator) / float(denominator)
    return round(percentage * 100, places)


def extract_attr(obj, name):
    parts = name.split('.')
    # Not likely
    if not parts:
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
