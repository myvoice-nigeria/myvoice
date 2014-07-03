# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'StatisticGroup'
        db.create_table(u'statistics_statisticgroup', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
        ))
        db.send_create_signal(u'statistics', ['StatisticGroup'])

        # Adding model 'Statistic'
        db.create_table(u'statistics_statistic', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('group', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['statistics.StatisticGroup'])),
            ('statistic_type', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal(u'statistics', ['Statistic'])


    def backwards(self, orm):
        # Deleting model 'StatisticGroup'
        db.delete_table(u'statistics_statisticgroup')

        # Deleting model 'Statistic'
        db.delete_table(u'statistics_statistic')


    models = {
        u'statistics.statistic': {
            'Meta': {'object_name': 'Statistic'},
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['statistics.StatisticGroup']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'statistic_type': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        u'statistics.statisticgroup': {
            'Meta': {'object_name': 'StatisticGroup'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        }
    }

    complete_apps = ['statistics']