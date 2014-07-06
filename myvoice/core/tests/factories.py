import datetime
import random
import string

import factory
import factory.django
import factory.fuzzy

from django.contrib.auth import models as auth
from django.utils import timezone

from myvoice.clinics import models as clinics
from myvoice.statistics import models as statistics
from myvoice.survey import models as survey

from rapidsms import models as rapidsms

from .utils import FuzzyBoolean, FuzzyEmail, FuzzyYear


class User(factory.django.DjangoModelFactory):
    FACTORY_FOR = auth.User

    email = FuzzyEmail()
    first_name = factory.fuzzy.FuzzyText()
    last_name = factory.fuzzy.FuzzyText()


class Clinic(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Clinic

    name = factory.Sequence(lambda n: 'PHC {0}'.format(n))
    slug = factory.Sequence(lambda n: 'phc-{0}'.format(n))
    town = factory.fuzzy.FuzzyText()
    ward = factory.fuzzy.FuzzyText()
    lga = factory.fuzzy.FuzzyText()
    code = factory.Sequence(lambda n: n)


class ClinicStaff(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.ClinicStaff

    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    name = factory.fuzzy.FuzzyText()
    staff_type = factory.fuzzy.FuzzyText()
    year_started = FuzzyYear()
    is_manager = FuzzyBoolean()


class Service(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Service

    name = factory.fuzzy.FuzzyText()
    code = factory.fuzzy.FuzzyInteger(0)


class Contact(factory.django.DjangoModelFactory):
    FACTORY_FOR = rapidsms.Contact

    name = factory.fuzzy.FuzzyText()


class Patient(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Patient

    name = factory.fuzzy.FuzzyText()
    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    serial = factory.fuzzy.FuzzyInteger(0)


class Visit(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Visit

    patient = factory.SubFactory('myvoice.core.tests.factories.Patient')
    service = factory.SubFactory('myvoice.core.tests.factories.Service')
    visit_time = factory.fuzzy.FuzzyDateTime(datetime.datetime(2014, 1, 1, tzinfo=timezone.utc))


class GenericFeedback(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.GenericFeedback

    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    sender = factory.fuzzy.FuzzyText()


class ClinicStatistic(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.ClinicStatistic

    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    statistic = factory.SubFactory('myvoice.core.tests.factories.Statistic')
    month = factory.LazyAttribute(lambda o: datetime.datetime.today())

    @factory.post_generation
    def value(self, create, extracted, **kwargs):
        if kwargs:
            raise Exception("value property does not support __")
        if extracted is None:
            statistic_type = self.statistic.statistic_type
            if statistic_type == statistics.Statistic.INTEGER:
                value = random.randint(0, 100)
            elif statistic_type in (statistics.Statistic.FLOAT, statistics.Statistic.PERCENTAGE):
                value = random.random() * 100
            elif statistic_type == statistics.Statistic.TEXT:
                value = ''.join([random.choice(string.letters) for i in range(12)])
            else:
                value = None
        else:
            value = extracted
        self.value = value
        if create:
            self.save()


class Statistic(factory.django.DjangoModelFactory):
    FACTORY_FOR = statistics.Statistic

    name = factory.Sequence(lambda n: 'Statistic {0}'.format(n))
    slug = factory.Sequence(lambda n: 'statistic-{0}'.format(n))
    group = factory.SubFactory('myvoice.core.tests.factories.StatisticGroup')

    @factory.lazy_attribute
    def statistic_type(self):
        choices = [k for k, _ in statistics.Statistic.STATISTIC_TYPES]
        return random.choice(choices)


class StatisticGroup(factory.django.DjangoModelFactory):
    FACTORY_FOR = statistics.StatisticGroup

    name = factory.Sequence(lambda n: 'Stat Group {0}'.format(n))
    slug = factory.Sequence(lambda n: 'stat-group-{0}'.format(n))


class Survey(factory.django.DjangoModelFactory):
    FACTORY_FOR = survey.Survey

    flow_id = factory.Sequence(lambda n: n)
    name = factory.fuzzy.FuzzyText()
    active = True
    role = survey.Survey.PATIENT_FEEDBACK
