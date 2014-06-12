import datetime
import re

from django.core.exceptions import ValidationError


def validate_year(value):
    if not re.match('\d\d\d\d', str(value)):
        raise ValidationError("Year must be in the format YYYY.")
    year = int(value)
    if year <= 1900:
        raise ValidationError("Please provide a year after 1900.")
    if year > datetime.date.today().year + 5:
        raise ValidationError("{0} is too far in the future.".format(year))
