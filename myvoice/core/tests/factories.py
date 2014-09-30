import datetime
import random

import factory
import factory.django
import factory.fuzzy

from django.contrib.auth import models as auth
from django.utils import timezone

from myvoice.clinics import models as clinics
from myvoice.survey import models as survey

from rapidsms import models as rapidsms

from .utils import FuzzyBoolean, FuzzyEmail, FuzzyYear


class User(factory.django.DjangoModelFactory):
    FACTORY_FOR = auth.User

    email = FuzzyEmail()
    first_name = factory.fuzzy.FuzzyText()
    last_name = factory.fuzzy.FuzzyText()


class Region(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Region

    name = factory.fuzzy.FuzzyText()
    external_id = factory.fuzzy.FuzzyInteger(1)
    type = factory.fuzzy.FuzzyChoice(clinics.Region.TYPE_CHIOCES)


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

    name = factory.Sequence(lambda n: 'Service {0}'.format(n))
    slug = factory.Sequence(lambda n: 'service-{0}'.format(n))
    code = factory.Sequence(lambda n: n)


class Contact(factory.django.DjangoModelFactory):
    FACTORY_FOR = rapidsms.Contact

    name = factory.fuzzy.FuzzyText()


class Patient(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Patient

    name = factory.fuzzy.FuzzyText()
    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    serial = factory.Sequence(lambda n: n)


class Visit(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.Visit

    patient = factory.SubFactory('myvoice.core.tests.factories.Patient')
    service = factory.SubFactory('myvoice.core.tests.factories.Service')
    visit_time = factory.fuzzy.FuzzyDateTime(datetime.datetime(2014, 1, 1, tzinfo=timezone.utc))


class GenericFeedback(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.GenericFeedback

    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    sender = factory.fuzzy.FuzzyText()


class ClinicScore(factory.django.DjangoModelFactory):
    FACTORY_FOR = clinics.ClinicScore

    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
    quality = factory.fuzzy.FuzzyDecimal(0.0, high=100.0)
    quantity = factory.fuzzy.FuzzyInteger(0)
    start_date = factory.fuzzy.FuzzyDateTime(datetime.datetime(2014, 1, 1, tzinfo=timezone.utc))
    end_date = factory.fuzzy.FuzzyDateTime(datetime.datetime(2014, 1, 1, tzinfo=timezone.utc))


class Survey(factory.django.DjangoModelFactory):
    FACTORY_FOR = survey.Survey

    flow_id = factory.Sequence(lambda n: n)
    name = factory.fuzzy.FuzzyText()
    active = True
    role = survey.Survey.PATIENT_FEEDBACK


class DisplayLabel(factory.django.DjangoModelFactory):
    FACTORY_FOR = survey.DisplayLabel

    name = factory.fuzzy.FuzzyText()


class SurveyQuestion(factory.django.DjangoModelFactory):
    FACTORY_FOR = survey.SurveyQuestion

    survey = factory.SubFactory('myvoice.core.tests.factories.Survey')
    question_id = factory.fuzzy.FuzzyText()
    label = factory.fuzzy.FuzzyText()
    report_order = factory.Sequence(lambda n: n)

    @factory.lazy_attribute
    def question_type(self):
        choices = [k for k, _ in survey.SurveyQuestion.QUESTION_TYPES]
        return random.choice(choices)


class SurveyQuestionResponse(factory.django.DjangoModelFactory):
    FACTORY_FOR = survey.SurveyQuestionResponse

    question = factory.SubFactory('myvoice.core.tests.factories.SurveyQuestion')
    response = factory.fuzzy.FuzzyText()
    datetime = factory.fuzzy.FuzzyDateTime(
        datetime.datetime(2014, 1, 1, tzinfo=timezone.utc))
    clinic = factory.SubFactory('myvoice.core.tests.factories.Clinic')
