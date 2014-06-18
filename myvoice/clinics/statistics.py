"""
The dashboard design expects very specific statistics, so we have hardcoded
the set of statistics which can be recorded. This set will grow with time.
"""

from collections import OrderedDict


# Statistic types
INTEGER = 'int'
FLOAT = 'float'
PERCENTAGE = 'percentage'
TEXT = 'text'

# Performance Summary statistics
INCOME = 'income'
QUALITY = 'quality'
SATISFACTION = 'satisfaction'

# Patient statistics
TOTAL_SEEN = 'patients-seen'
OUTREACH = 'outreach'
IN_FACILITY = 'in-facility'
INDIGENTS = 'indigents'

# Service statistics
# NOTE: Not every clinic will offer every service in a given month. These
# choices constitute a canonical reference for any service that a clinic might
# offer.
DELIVERY = 'delivery'
OUTPATIENT = 'outpatient'
FAMILY_PLANNING = 'family-planning'
TESTS = 'tests'
STD = 'std'
OTHER = 'other'


# This map keeps all statistic metadata compact and together, since the
# number of statistics will grow with time. Prefer the utility methods below
# to using this map directly.
# NOTE: Take care when changing the type of a statistic - the stored value
# associated with ClinicStatistic instances will have to be updated.
_STATISTICS_MAP = OrderedDict([
    (INCOME, {'type': INTEGER, 'desc': 'Income'}),
    (QUALITY, {'type': PERCENTAGE, 'desc': 'Quality Score'}),
    (SATISFACTION, {'type': PERCENTAGE, 'desc': 'Patient Satisfaction'}),

    (TOTAL_SEEN, {'type': INTEGER, 'desc': 'Total Patients Seen'}),
    (OUTREACH, {'type': INTEGER, 'desc': 'Outreach'}),
    (IN_FACILITY, {'type': INTEGER, 'desc': 'In Facility'}),
    (INDIGENTS, {'type': INTEGER, 'desc': 'Indigents'}),

    (DELIVERY, {'type': PERCENTAGE, 'desc': 'Normal Delivery'}),
    (OUTPATIENT, {'type': PERCENTAGE, 'desc': 'New Outpatient Consultation'}),
    (FAMILY_PLANNING, {'type': PERCENTAGE, 'desc': 'Family Planning'}),
    (TESTS, {'type': PERCENTAGE, 'desc': 'VCT/PMTCT/PIT Tests'}),
    (STD, {'type': PERCENTAGE, 'desc': 'STD Treatment'}),
    (OTHER, {'type': PERCENTAGE, 'desc': 'Other Services'}),
])


def get_statistic_choices():
    """Returns a Django-style choices list for a model or form field."""
    return [(key, value['desc']) for key, value in _STATISTICS_MAP.items()]


def get_statistic_type(statistic):
    """Returns the type of the statistic if it is known, or None.

    Statistic types are INTEGER, FLOAT, PERCENTAGE, or TEXT.
    """
    if statistic in _STATISTICS_MAP:
        return _STATISTICS_MAP.get(statistic)['type']
    return None


def get_statistic_display(statistic):
    """
    Returns the display description of the statistic if it is known, or None.
    """
    if statistic in _STATISTICS_MAP:
        return _STATISTICS_MAP.get(statistic)['desc']
    return None
