import datetime
import random
import string

import factory
import factory.django
import factory.fuzzy

from django.contrib.auth import models as auth

from myvoice.clinics import statistics
from myvoice.clinics import models as clinics

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


class Visit(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Visit

    patient = factory.SubFactory('myvoice.core.tests.factories.Patient')
    service = factory.SubFactory('myvoice.core.tests.factories.Service')


class ClinicStatistic(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.ClinicStatistic

    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    month = factory.LazyAttribute(lambda o: datetime.datetime.today())

    @factory.lazy_attribute
    def statistic(self):
        choices = [c[0] for c in statistics.get_statistic_choices()]
        return random.choice(choices)

    @factory.post_generation
    def value(self, create, extracted, **kwargs):
        if kwargs:
            raise Exception("value property does not support __")
        if extracted is None:
            statistic_type = self.get_statistic_type()
            if statistic_type == statistics.INTEGER:
                value = random.randint(0, 100)
            elif statistic_type in (statistics.FLOAT, statistics.PERCENTAGE):
                value = random.random() * 100
            elif statistic_type == statistics.TEXT:
                value = ''.join([random.choice(string.letters) for i in range(12)])
            else:
                value = None
        else:
            value = extracted
        self.value = value
        if create:
            self.save()
