# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):
    depends_on = [
        ('survey', '0005_auto__del_field_surveyquestion_statistic'),
        ('clinics', '0028_auto__del_clinicstatistic__del_unique_clinicstatistic_clinic_statistic'),
    ]

    def forwards(self, orm):
        # Deleting model 'Statistic'
        db.delete_table(u'statistics_statistic')

        # Deleting model 'StatisticGroup'
        db.delete_table(u'statistics_statisticgroup')


    def backwards(self, orm):
        # Adding model 'Statistic'
        db.create_table(u'statistics_statistic', (
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['statistics.StatisticGroup'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('statistic_type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, unique=True)),
        ))
        db.send_create_signal(u'statistics', ['Statistic'])

        # Adding model 'StatisticGroup'
        db.create_table(u'statistics_statisticgroup', (
            ('slug', self.gf('django.db.models.fields.SlugField')(max_length=50, unique=True)),
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, unique=True)),
        ))
        db.send_create_signal(u'statistics', ['StatisticGroup'])


    models = {

    }

    complete_apps = ['statistics']
