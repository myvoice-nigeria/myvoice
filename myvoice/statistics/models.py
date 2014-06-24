from django.db import models


class StatisticGroup(models.Model):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)

    def __unicode__(self):
        return self.name


class Statistic(models.Model):
    TEXT = 'text'
    FLOAT = 'float'
    INTEGER = 'int'
    PERCENTAGE = 'percentage'
    STATISTIC_TYPES = (
        (TEXT, 'Text'),
        (FLOAT, 'Float'),
        (INTEGER, 'Integer'),
        (PERCENTAGE, 'Percentage'),
    )

    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(unique=True)
    group = models.ForeignKey('StatisticGroup')
    statistic_type = models.CharField(max_length=32, choices=STATISTIC_TYPES)

    def __unicode__(self):
        return self.name
