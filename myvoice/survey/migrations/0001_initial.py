# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Survey'
        db.create_table(u'survey_survey', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('flow_id', self.gf('django.db.models.fields.IntegerField')(unique=True, max_length=32)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
            ('active', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'survey', ['Survey'])

        # Adding model 'SurveyQuestion'
        db.create_table(u'survey_surveyquestion', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('survey', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['survey.Survey'])),
            ('question_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('question_type', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('categories', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('designation', self.gf('django.db.models.fields.CharField')(default='unknown', max_length=8)),
            ('order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('statistic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['statistics.Statistic'], null=True, blank=True)),
        ))
        db.send_create_signal(u'survey', ['SurveyQuestion'])

        # Adding unique constraint on 'SurveyQuestion', fields ['survey', 'label']
        db.create_unique(u'survey_surveyquestion', ['survey_id', 'label'])

        # Adding model 'SurveyQuestionResponse'
        db.create_table(u'survey_surveyquestionresponse', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('run_id', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('connection', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rapidsms.Connection'])),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['survey.SurveyQuestion'])),
            ('clinic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['clinics.Clinic'], null=True, blank=True)),
            ('response', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('datetime', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('updated', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal(u'survey', ['SurveyQuestionResponse'])

        # Adding unique constraint on 'SurveyQuestionResponse', fields ['run_id', 'question']
        db.create_unique(u'survey_surveyquestionresponse', ['run_id', 'question_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'SurveyQuestionResponse', fields ['run_id', 'question']
        db.delete_unique(u'survey_surveyquestionresponse', ['run_id', 'question_id'])

        # Removing unique constraint on 'SurveyQuestion', fields ['survey', 'label']
        db.delete_unique(u'survey_surveyquestion', ['survey_id', 'label'])

        # Deleting model 'Survey'
        db.delete_table(u'survey_survey')

        # Deleting model 'SurveyQuestion'
        db.delete_table(u'survey_surveyquestion')

        # Deleting model 'SurveyQuestionResponse'
        db.delete_table(u'survey_surveyquestionresponse')


    models = {
        u'clinics.clinic': {
            'Meta': {'object_name': 'Clinic'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Contact']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_renovated': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'lga': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'lga_rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'location': ('django.contrib.gis.db.models.fields.PointField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'pbf_rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'ward': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'year_opened': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'})
        },
        u'rapidsms.backend': {
            'Meta': {'object_name': 'Backend'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'})
        },
        u'rapidsms.connection': {
            'Meta': {'unique_together': "(('backend', 'identity'),)", 'object_name': 'Connection'},
            'backend': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Backend']"}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Contact']", 'null': 'True', 'blank': 'True'}),
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'identity': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'modified_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'rapidsms.contact': {
            'Meta': {'object_name': 'Contact'},
            'created_on': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '6', 'blank': 'True'}),
            'modified_on': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'})
        },
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
        },
        u'survey.survey': {
            'Meta': {'object_name': 'Survey'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'flow_id': ('django.db.models.fields.IntegerField', [], {'unique': 'True', 'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'survey.surveyquestion': {
            'Meta': {'ordering': "['order', 'id']", 'unique_together': "[('survey', 'label')]", 'object_name': 'SurveyQuestion'},
            'categories': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'designation': ('django.db.models.fields.CharField', [], {'default': "'unknown'", 'max_length': '8'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'question_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'question_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['statistics.Statistic']", 'null': 'True', 'blank': 'True'}),
            'survey': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['survey.Survey']"})
        },
        u'survey.surveyquestionresponse': {
            'Meta': {'unique_together': "[('run_id', 'question')]", 'object_name': 'SurveyQuestionResponse'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']", 'null': 'True', 'blank': 'True'}),
            'connection': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Connection']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['survey.SurveyQuestion']"}),
            'response': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'run_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['survey']