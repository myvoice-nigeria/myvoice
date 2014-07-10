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


def extract_qset_data(qset, fld_names):
    """Extract data from queryset for export to CSV file."""
    #fld_names = [fld for fld in qset.model._meta.fields.get_all_field_names()
    #             if fld not in ['id']]
    out = [[i for i in fld_names]]
    for obj in qset:
        line = [str(getattr(obj, fld_name)).decode('utf-8', 'ignore')
                for fld_name in fld_names]
        out.append(line)
    return out
