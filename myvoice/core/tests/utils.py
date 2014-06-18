import datetime

import factory.fuzzy


class FuzzyYear(factory.fuzzy.FuzzyInteger):

    def __init__(self):
        low = 1901
        high = datetime.date.today().year + 5
        super(FuzzyYear, self).__init__(low, high)


class FuzzyBoolean(factory.fuzzy.FuzzyChoice):

    def __init__(self):
        choices = (True, False)
        super(FuzzyBoolean, self).__init__(choices)


class FuzzyEmail(factory.fuzzy.FuzzyText):

    def fuzz(self):
        return super(FuzzyEmail, self).fuzz() + '@example.com'
