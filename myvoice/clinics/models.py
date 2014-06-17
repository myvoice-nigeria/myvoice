from django.db import models
from django.core.exceptions import ValidationError

from myvoice.core.validators import validate_year

from . import statistics


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

    category = models.CharField(max_length=32, blank=True)
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


class ClinicStatistic(models.Model):
    """
    A statistic about a Clinic, valid in a given month.

    Each month, data about clinics is posted at nphcda.thenewtechs.com. We
    regularly scrape, extract, and analyze this data, and store it using this
    model.
    """
    clinic = models.ForeignKey('Clinic')
    month = models.DateField()

    # NOTE: Take care when changing the statistic - the stored value
    # associated with this instance will have to be updated if the type
    # changes.
    statistic = models.CharField(
        max_length=8, choices=statistics.get_statistic_choices(),
        help_text="Statistic choices are hard-coded. If you do not see the "
        "statistic you want, it must be added programatically. Each statistic "
        "is associated with a data type (integer, float, percentage, or text) "
        "that will determine how the value you enter is displayed.")

    # In general, do not access these directly - use the `value` property and
    # `get_value_display()` instead.
    float_value = models.FloatField(null=True, blank=True, editable=False)
    int_value = models.IntegerField(null=True, blank=True, editable=False)
    text_value = models.CharField(
        max_length=255, null=True, blank=True, editable=False)

    # In general, this will be calculated programatically.
    rank = models.IntegerField(blank=True, null=True, editable=False)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('clinic', 'statistic', 'month')]
        verbose_name = 'statistic'

    def __unicode__(self):
        return '{statistic} for {clinic} for {month}'.format(
            statistic=self.statistic, clinic=self.clinic.name,
            month=self.get_month_display())

    def _get_value(self):
        """Retrieve this statistic's value based on its type."""
        statistic_type = self.get_statistic_type()
        if statistic_type in (statistics.FLOAT, statistics.PERCENTAGE):
            return self.float_value
        elif statistic_type in (statistics.INTEGER,):
            return self.int_value
        elif statistic_type in (statistics.TEXT,):
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
        statistic_type = self.get_statistic_type()
        if statistic_type in (statistics.FLOAT, statistics.PERCENTAGE):
            self.float_value = value
            self.int_value = None
            self.text_value = None
        elif statistic_type in (statistics.INTEGER,):
            self.float_value = None
            self.int_value = value
            self.text_value = None
        elif statistic_type in (statistics.TEXT,):
            self.float_value = None
            self.int_value = None
            self.text_value = value
        else:
            raise Exception("Attempted to set value before statistic type "
                            "was set.")

    value = property(_get_value, _set_value,
                     doc="The value of this statistic.")

    def validate_value(self):
        """
        Ensures that an appropriate value is being used for the statistic's
        type.

        NOTE: This must be called and handled before saving a statistic,
        to avoid storing values that are inappropriate for the statistic type.
        It is not called by default during save(). For an example of how to
        incorporate this into a model form, see
        myvoice.clinics.forms.ClinicStatisticAdminForm.
        """
        statistic_type = self.get_statistic_type()
        if statistic_type in (statistics.FLOAT, statistics.PERCENTAGE):
            try:
                float(self.float_value)
            except (ValueError, TypeError):
                error_msg = '{0} requires a non-null float value.'
                raise ValidationError({
                    'value': [error_msg.format(self.get_statistic_display())],
                })
        elif statistic_type in (statistics.INTEGER,):
            try:
                int(self.int_value)
            except (ValueError, TypeError):
                error_msg = '{0} requires a non-null integer value.'
                raise ValidationError({
                    'value': [error_msg.format(self.get_statistic_display())],
                })
        elif statistic_type in (statistics.TEXT,):
            if self.text_value is None:
                error_msg = '{0} requires a non-null text value.'
                raise ValidationError({
                    'value': [error_msg.format(self.get_statistic_display())],
                })
        else:
            # Either the statistic field has not been set, is invalid, or
            # we have forgotten to include the correct information in the
            # myvoice.clinics.statistics module.
            raise ValidationError({
                'statistic': ["Unable to determine statistic type."],
            })

    def get_month_display(self, frmt='%B %Y'):
        return self.month.strftime(frmt)

    def get_value_display(self):
        statistic_type = self.get_statistic_type()
        if statistic_type == statistics.PERCENTAGE:
            return '{0}%'.format(self.value)
        return self.value

    def get_statistic_type(self):
        return statistics.get_statistic_type(self.statistic)
