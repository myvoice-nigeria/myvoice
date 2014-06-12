from django.db import models

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
        'rapidsms.Contact', verbose_name='Preferred contact')
    year_opened = models.CharField(
        max_length=4, blank=True, validators=[validate_year],
        help_text="Please enter a four-digit year.")
    last_renovated = models.CharField(
        max_length=4, blank=True, validators=[validate_year],
        help_text="Please enter a four-digit year.")

    lga_rank = models.IntegerField(
        blank=True, null=True, verbose_name='LGA rank')
    pbf_rank = models.IntegerField(
        blank=True, null=True, verbose_name='PBF rank')

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

    statistic = models.CharField(
        max_length=8, choices=statistics.get_statistic_choices(),
        help_text="Statistic choices are hard-coded. If you do not see the "
        "statistic you want, it must be added programatically. Each statistic "
        "is associated with a data type (integer, float, percentage, or text) "
        "that will determine how the value you enter is displayed.")

    value = models.CharField(max_length=255, blank=True)

    # In general, this will be calculated programatically.
    rank = models.IntegerField(blank=True, null=True)

    class Meta:
        unique_together = [('clinic', 'statistic', 'month')]
        verbose_name = 'statistic'

    def __unicode__(self):
        return '{statistic} for {clinic} for {month}'.format(
            statistic=self.statistic, clinic=self.clinic.name,
            month=self.get_month_display())

    def clean(self):
        value_type = self.get_value_type()
        if not value_type:
            # Either the given statistic is invalid, or we didn't give the
            # necessary data about it in the statistics model.
            raise ValidationError("Unable to determine the value type of "
                                  "{0}.".format(self.statistic))
        elif value_type in (statistics.INTEGER,):
            # Value must validate as an integer.
            try:
                int(self.value)
            except (ValueError, TypeError):
                raise ValidationError("{0} requires an integer "
                                      "value.".format(self.statistic))
        if value_type in (statistics.FLOAT, statistics.PERCENTAGE):
            # Value must validate as a float.
            try:
                float(self.value)
            except (ValueError, TypeError):
                raise ValidationError("")
        else:
            # Value is just text, and requires no special validation.
            pass
        return super(ClinicStatistic, self).clean()

    def get_month_display(self, frmt='%B %Y'):
        return self.month.strftime(frmt)

    def get_value_display(self):
        value_type = self.get_value_type()
        if value_type == statistics.PERCENTAGE:
            return '{0}%'.format(self.value)
        return self.value

    def get_value_type(self):
        return statistics.get_statistic_type(self.statistic)
