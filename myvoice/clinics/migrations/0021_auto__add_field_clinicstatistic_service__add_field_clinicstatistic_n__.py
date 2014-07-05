# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        try:
            # Removing unique constraint on 'ClinicStatistic', fields ['clinic', 'statistic', 'month']
            db.delete_unique(u'clinics_clinicstatistic', ['clinic_id', 'statistic_id', 'month'])
        except:
            # FIXME: Sometimes this fails saying that the unique constraint
            # isn't present. For now, that's good enough.
            pass

        # Adding field 'ClinicStatistic.service'
        db.add_column(u'clinics_clinicstatistic', 'service',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['clinics.Service'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'ClinicStatistic.n'
        db.add_column(u'clinics_clinicstatistic', 'n',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


        # Changing field 'ClinicStatistic.clinic'
        db.alter_column(u'clinics_clinicstatistic', 'clinic_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['clinics.Clinic'], null=True))
        # Adding unique constraint on 'ClinicStatistic', fields ['clinic', 'service', 'statistic', 'month']
        db.create_unique(u'clinics_clinicstatistic', ['clinic_id', 'service_id', 'statistic_id', 'month'])


    def backwards(self, orm):
        # Removing unique constraint on 'ClinicStatistic', fields ['clinic', 'service', 'statistic', 'month']
        db.delete_unique(u'clinics_clinicstatistic', ['clinic_id', 'service_id', 'statistic_id', 'month'])

        # Deleting field 'ClinicStatistic.service'
        db.delete_column(u'clinics_clinicstatistic', 'service_id')

        # Deleting field 'ClinicStatistic.n'
        db.delete_column(u'clinics_clinicstatistic', 'n')


        # Changing field 'ClinicStatistic.clinic'
        db.alter_column(u'clinics_clinicstatistic', 'clinic_id', self.gf('django.db.models.fields.related.ForeignKey')(default=0, to=orm['clinics.Clinic']))
        # Adding unique constraint on 'ClinicStatistic', fields ['clinic', 'statistic', 'month']
        db.create_unique(u'clinics_clinicstatistic', ['clinic_id', 'statistic_id', 'month'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
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
        u'clinics.clinicstaff': {
            'Meta': {'object_name': 'ClinicStaff'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']"}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Contact']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_manager': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'staff_type': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'year_started': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'})
        },
        u'clinics.clinicstatistic': {
            'Meta': {'unique_together': "[('clinic', 'service', 'statistic', 'month')]", 'object_name': 'ClinicStatistic'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']", 'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'month': ('django.db.models.fields.DateField', [], {}),
            'n': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Service']", 'null': 'True', 'blank': 'True'}),
            'statistic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['statistics.Statistic']"}),
            'text_value': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        u'clinics.genericfeedback': {
            'Meta': {'object_name': 'GenericFeedback'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'message_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sender': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'clinics.patient': {
            'Meta': {'object_name': 'Patient'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']", 'null': 'True', 'blank': 'True'}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Contact']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mobile': ('django.db.models.fields.CharField', [], {'max_length': '11', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50', 'blank': 'True'}),
            'serial': ('django.db.models.fields.PositiveIntegerField', [], {})
        },
        u'clinics.region': {
            'Meta': {'unique_together': "(('external_id', 'type'),)", 'object_name': 'Region'},
            'alternate_name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'boundary': ('django.contrib.gis.db.models.fields.MultiPolygonField', [], {}),
            'external_id': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'lga'", 'max_length': '16'})
        },
        u'clinics.service': {
            'Meta': {'object_name': 'Service'},
            'code': ('django.db.models.fields.PositiveIntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'})
        },
        u'clinics.visit': {
            'Meta': {'object_name': 'Visit'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'patient': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Patient']"}),
            'service': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Service']", 'null': 'True', 'blank': 'True'}),
            'staff': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.ClinicStaff']", 'null': 'True', 'blank': 'True'}),
            'survey_sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'visit_time': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        },
        u'clinics.visitregistrationerror': {
            'Meta': {'object_name': 'VisitRegistrationError'},
            'error_type': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'sender': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'clinics.visitregistrationerrorlog': {
            'Meta': {'object_name': 'VisitRegistrationErrorLog'},
            'error_type': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '160'}),
            'message_date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'sender': ('django.db.models.fields.CharField', [], {'max_length': '20'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
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
        }
    }

    complete_apps = ['clinics']
