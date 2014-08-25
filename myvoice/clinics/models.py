from django.contrib.gis.db import models as gis
from django.db import models
from django.utils import timezone

from myvoice.core.validators import validate_year


class Region(gis.Model):
    """Geographical regions"""
    TYPE_CHIOCES = (
        ('country', 'Country'),
        ('state', 'State'),
        ('lga', 'LGA'),
    )
    name = models.CharField(max_length=255)
    alternate_name = models.CharField(max_length=255, blank=True)
    type = models.CharField(max_length=16, choices=TYPE_CHIOCES, default='lga')
    external_id = models.IntegerField("External ID")
    boundary = gis.MultiPolygonField()

    objects = gis.GeoManager()

    class Meta(object):
        unique_together = ('external_id', 'type')

    def __unicode__(self):
        return u"{} - {}".format(self.get_type_display(), self.name)


class Clinic(models.Model):
    """A health clinic."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)

    # These might later become location-based models. LGA should be
    # easily accessible (not multiple foreign keys away) since it is the
    # designator that we are most interested in.
    town = models.CharField(max_length=100)
    ward = models.CharField(max_length=100)
    lga = models.CharField(max_length=100, verbose_name='LGA')
    location = gis.PointField(null=True, blank=True)

    lga_rank = models.IntegerField(
        blank=True, null=True, verbose_name='LGA rank', editable=False)
    pbf_rank = models.IntegerField(
        blank=True, null=True, verbose_name='PBF rank', editable=False)

    code = models.PositiveIntegerField(
        verbose_name='SMS Code', unique=True,
        help_text="Code of Clinic to be used in SMS registration.")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    objects = gis.GeoManager()

    def __unicode__(self):
        return self.name

    def managers(self):
        """The staff members who are in charge of this clinic."""
        return self.clinicstaff_set.filter(is_manager=True)


class ClinicStaff(models.Model):
    """Represents a person who works at a Clinic."""
    clinic = models.ForeignKey('Clinic')

    user = models.ForeignKey(
        'auth.User', blank=True, null=True,
        help_text="If possible, this person should have a User account.")
    name = models.CharField(
        max_length=100, blank=True,
        help_text="If given, the User account's name will be preferred to the "
        "name given here with the assumption that it is more likely to be "
        "current.")
    contact = models.ForeignKey(
        'rapidsms.Contact', verbose_name='Preferred contact', blank=True, null=True,
        help_text="If not given but a User is associated with this person, "
        "the User's first associated Contact may be used.")

    # It would be nice to make this a choice field if we could get a list
    # of all possible staff position types.
    staff_type = models.CharField(max_length=100)

    year_started = models.CharField(
        max_length=4, blank=True, validators=[validate_year],
        help_text="Please enter a four-digit year.")
    is_manager = models.BooleanField(
        default=False,
        help_text="Whether this person is considered in charge of the clinic.")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return self.get_name_display()

    def get_name_display(self):
        """Prefer the associated User's name to the name specified here."""
        return self.user.get_full_name() if self.user else self.name


class Service(models.Model):
    """A medical service offered by a Clinic."""
    name = models.CharField(max_length=128)
    slug = models.SlugField(unique=True)
    code = models.PositiveIntegerField(
        verbose_name='SMS Code', unique=True,
        help_text="Code of Service to be used in SMS registration.")

    def __unicode__(self):
        return self.name


class Patient(models.Model):
    """Represents a patient at the Clinic."""
    name = models.CharField(max_length=50, blank=True)
    clinic = models.ForeignKey('Clinic', blank=True, null=True)
    mobile = models.CharField(max_length=11, blank=True)
    serial = models.PositiveIntegerField()

    class Meta:
        unique_together = [('clinic', 'serial')]

    def __unicode__(self):
        return u'{0} at {1}'.format(self.serial, self.clinic.name)


class Visit(models.Model):
    """Represents a visit of a Patient to the Clinic."""
    patient = models.ForeignKey('Patient')
    service = models.ForeignKey('Service', blank=True, null=True)
    staff = models.ForeignKey('ClinicStaff', blank=True, null=True)
    visit_time = models.DateTimeField(default=timezone.now)

    # welcome_sent is used to signify that a message is new (value is null).
    # Welcome messages are no longer sent.
    # See issue: https://github.com/myvoice-nigeria/myvoice/issues/207
    welcome_sent = models.DateTimeField(blank=True, null=True)
    survey_sent = models.DateTimeField(blank=True, null=True)
    mobile = models.CharField(max_length=11, blank=True)
    sender = models.CharField(max_length=11, blank=True)

    # The following fields denormalize to help reporting
    # so questions are more flexible.
    satisfied = models.NullBooleanField()
    survey_started = models.BooleanField(default=False)
    survey_completed = models.BooleanField(default=False)

    def __unicode__(self):
        return unicode(self.patient)


class VisitRegistrationError(models.Model):
    """Keeps current state of errors in Visit registration SMS.

    Right now, only "wrong clinic" is useful."""

    WRONG_CLINIC = 0
    WRONG_MOBILE = 1
    WRONG_SERIAL = 2
    WRONG_SERVICE = 3

    ERROR_TYPES = enumerate(('Wrong Clinic', 'Wrong Mobile', 'Wrong Serial', 'Wrong Service'))

    sender = models.CharField(max_length=20)
    error_type = models.PositiveIntegerField(choices=ERROR_TYPES, default=WRONG_CLINIC)

    def __unicode__(self):
        return self.sender


class VisitRegistrationErrorLog(models.Model):
    """Keeps log of errors in Visit registration SMS."""
    sender = models.CharField(max_length=20)
    error_type = models.CharField(max_length=50)
    message_date = models.DateTimeField(auto_now=True)
    message = models.CharField(max_length=160)

    def __unicode__(self):
        return self.sender


class GenericFeedback(models.Model):
    """Keeps Feedback information sent by patients."""
    sender = models.CharField(max_length=20)
    clinic = models.ForeignKey('Clinic', null=True, blank=True)
    message = models.TextField(blank=True)
    message_date = models.DateTimeField(auto_now=True)
    display_on_dashboard = models.BooleanField(
        default=True,
        help_text="Whether or not this response is displayed on the dashboard.")

    class Meta:
        verbose_name = 'General Feedback'
        verbose_name_plural = 'General Feedback'

    def __unicode__(self):
        return self.sender
