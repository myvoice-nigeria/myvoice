import datetime


def get_week_start(date):
    days_since_monday = date.weekday()
    monday = date - datetime.timedelta(days=days_since_monday)
    monday = monday.replace(microsecond=0, second=0, minute=0, hour=0)
    return monday


def get_week_end(date):
    return get_week_start(date) + datetime.timedelta(days=7, microseconds=-1)
