from django.db import models
from django.contrib.gis.db import models as gis
from django.core.exceptions import ValidationError

from myvoice.core.validators import validate_year
from myvoice.statistics.models import Statistic


class Region(gis.Model):
    """Geographical regions"""
    TYPE_CHIOCES = (
        ('country', 'Country'),
        ('state', 'State'),
        ('lga', 'Local Government Area'),
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
        return "{} - {}".format(self.get_type_display(), self.name)


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

    category = models.CharField(
        max_length=32, blank=True, verbose_name='PBF category')
    contact = models.ForeignKey(
        'rapidsms.Contact', blank=True, null=True,
        verbose_name='Preferred contact')
    year_opened = models.CharField(
        max_length=4, blank=True, validators=[validate_year],
        help_text="Please enter a four-digit year.")
    last_renovated = models.CharField(
        max_length=4, blank=True, validators=[validate_year],
        help_text="Please enter a four-digit year.")

    lga_rank = models.IntegerField(
        blank=True, null=True, verbose_name='LGA rank', editable=False)
    pbf_rank = models.IntegerField(
        blank=True, null=True, verbose_name='PBF rank', editable=False)

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

    def __unicode__(self):
        return self.name


class Patient(models.Model):
    """Represents a patient at the Clinic."""
    name = models.CharField(max_length=50, blank=True)
    clinic = models.ForeignKey('Clinic')
    contact = models.ForeignKey(
        'rapidsms.Contact', verbose_name='Preferred contact',
        blank=True, null=True)

    def __unicode__(self):
        return self.get_name_display()

    def get_name_display(self):
        """Prefer the associated Contact's name to the name here."""
        return self.contact.name if self.contact else self.name


class Visit(models.Model):
    """Represents a visit of a Patient to the Clinic."""
    patient = models.ForeignKey('Patient')
    service_type = models.CharField(max_length=50)
    staff = models.ForeignKey('ClinicStaff', blank=True, null=True)
    visit_time = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return unicode(self.patient)


class ClinicStatistic(models.Model):
    """
    A statistic about a Clinic, valid in a given month.

    Each month, data about clinics is posted at nphcda.thenewtechs.com. We
    regularly scrape, extract, and analyze this data, and store it using this
    model.
    """
    clinic = models.ForeignKey('Clinic')
    month = models.DateField()

    # NOTE: Take care when changing the statistic or its type - the stored
    # value associated with this instance will have to be updated if the type
    # changes.
    statistic = models.ForeignKey('statistics.Statistic')

    # In general, do not access these directly - use the `value` property and
    # `get_value_display()` instead.
    float_value = models.FloatField(null=True, blank=True, editable=False)
    int_value = models.IntegerField(null=True, blank=True, editable=False)
    text_value = models.CharField(
        max_length=255, null=True, blank=True, editable=False)

    # In general, this will be calculated programatically.
    rank = models.IntegerField(
        blank=True, null=True, editable=False,
        help_text="The rank of this clinic against others for the same "
        "statistic and month.")

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('clinic', 'statistic', 'month')]
        verbose_name = 'statistic'

    def __unicode__(self):
        return '{statistic} for {clinic} for {month}'.format(
            statistic=self.get_statistic_display(), clinic=self.clinic.name,
            month=self.get_month_display())

    def _get_value(self):
        """Retrieve this statistic's value based on its type."""
        statistic_type = self.statistic.statistic_type
        if statistic_type in (Statistic.FLOAT, Statistic.PERCENTAGE):
            return self.float_value
        elif statistic_type in (Statistic.INTEGER,):
            return self.int_value
        elif statistic_type in (Statistic.TEXT,):
            return self.text_value
        else:
            raise Exception("Attempted to retrieve value before statistic "
                            "type was set.")

    def _set_value(self, value):
        """Set this statistic's value based on its type.

        Also clears the non-relevant value fields. No validation is done
        here - just like with a normal Django field, it will be validated
        when the model is cleaned.
        """
        statistic_type = self.statistic.statistic_type
        if statistic_type in (Statistic.FLOAT, Statistic.PERCENTAGE):
            self.float_value = value
            self.int_value = None
            self.text_value = None
        elif statistic_type in (Statistic.INTEGER,):
            self.float_value = None
            self.int_value = value
            self.text_value = None
        elif statistic_type in (Statistic.TEXT,):
            self.float_value = None
            self.int_value = None
            self.text_value = value
        else:
            raise Exception("Attempted to set value before statistic type "
                            "was set.")

    value = property(_get_value, _set_value,
                     doc="The value of this statistic.")

    def clean_value(self):
        """
        Ensures that an appropriate value is being used for the statistic's
        type.

        NOTE: This must be called and handled before saving a statistic,
        to avoid storing values that are inappropriate for the statistic type.
        It is not called by default during save(). For an example of how to
        incorporate this into a model form, see
        myvoice.clinics.forms.ClinicStatisticAdminForm.
        """
        statistic_type = self.statistic.statistic_type
        if statistic_type in (Statistic.FLOAT, Statistic.PERCENTAGE):
            try:
                self.float_value = float(self.float_value)
            except (ValueError, TypeError):
                error_msg = '{0} requires a non-null float value.'
                raise ValidationError({
                    'value': [error_msg.format(self.get_statistic_display())],
                })
        elif statistic_type in (Statistic.INTEGER,):
            try:
                self.int_value = int(self.int_value)
            except (ValueError, TypeError):
                error_msg = '{0} requires a non-null integer value.'
                raise ValidationError({
                    'value': [error_msg.format(self.get_statistic_display())],
                })
        elif statistic_type in (Statistic.TEXT,):
            if self.text_value is None:
                error_msg = '{0} requires a non-null text value.'
                raise ValidationError({
                    'value': [error_msg.format(self.get_statistic_display())],
                })
            self.text_value = str(self.text_value)
        else:
            raise ValidationError({
                'statistic': ["Unable to determine statistic type."],
            })

    def get_month_display(self, frmt='%B %Y'):
        return self.month.strftime(frmt)

    def get_value_display(self):
        statistic_type = self.statistic.statistic_type
        if statistic_type == Statistic.PERCENTAGE:
            return '{0}%'.format(round(self.value, 1))
        elif statistic_type == Statistic.FLOAT:
            return '{0}'.format(round(self.value, 1))
        return self.value
