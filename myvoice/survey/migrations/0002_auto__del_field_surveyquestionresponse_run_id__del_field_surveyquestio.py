# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'SurveyQuestionResponse', fields ['run_id', 'question']
        db.delete_unique(u'survey_surveyquestionresponse', ['run_id', 'question_id'])

        # Deleting field 'SurveyQuestionResponse.run_id'
        db.delete_column(u'survey_surveyquestionresponse', 'run_id')

        # Deleting field 'SurveyQuestionResponse.connection'
        db.delete_column(u'survey_surveyquestionresponse', 'connection_id')

        # Adding field 'SurveyQuestionResponse.phone'
        db.add_column(u'survey_surveyquestionresponse', 'phone',
                      self.gf('django.db.models.fields.CharField')(default='1', max_length=32),
                      keep_default=False)

        # Adding unique constraint on 'SurveyQuestionResponse', fields ['phone', 'question']
        db.create_unique(u'survey_surveyquestionresponse', ['phone', 'question_id'])


    def backwards(self, orm):
        # Removing unique constraint on 'SurveyQuestionResponse', fields ['phone', 'question']
        db.delete_unique(u'survey_surveyquestionresponse', ['phone', 'question_id'])

        # Adding field 'SurveyQuestionResponse.run_id'
        db.add_column(u'survey_surveyquestionresponse', 'run_id',
                      self.gf('django.db.models.fields.CharField')(default=1, max_length=128),
                      keep_default=False)

        # Adding field 'SurveyQuestionResponse.connection'
        db.add_column(u'survey_surveyquestionresponse', 'connection',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['rapidsms.Connection']),
                      keep_default=False)

        # Deleting field 'SurveyQuestionResponse.phone'
        db.delete_column(u'survey_surveyquestionresponse', 'phone')

        # Adding unique constraint on 'SurveyQuestionResponse', fields ['run_id', 'question']
        db.create_unique(u'survey_surveyquestionresponse', ['run_id', 'question_id'])


    models = {
        u'clinics.clinic': {
            'Meta': {'object_name': 'Clinic'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'code': ('django.db.models.fields.PositiveIntegerField', [], {'unique': 'True'}),
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
        u'clinics.service': {
            'Meta': {'object_name': 'Service'},
            'code': ('django.db.models.fields.PositiveIntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'role': ('django.db.models.fields.CharField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'survey.surveyquestion': {
            'Meta': {'ordering': "['order', 'id']", 'unique_together': "[('survey', 'label')]", 'object_name': 'SurveyQuestion'},
            'categories': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'designation': ('django.db.models.fields.CharField', [], {'default': "'unknown'", 'max_length': '8'}),
            'for_display': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'question_id': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'question_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['statistics.Statistic']", 'null': 'True', 'blank': 'True'}),
            'survey': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['survey.Survey']"})
        },
        u'survey.surveyquestionresponse': {
            'Meta': {'unique_together': "[('phone', 'question')]", 'object_name': 'SurveyQuestionResponse'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'datetime': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['survey.SurveyQuestion']"}),
            'response': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Service']", 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['survey']