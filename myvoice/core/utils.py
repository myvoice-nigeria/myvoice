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
