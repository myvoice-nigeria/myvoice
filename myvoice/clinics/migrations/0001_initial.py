# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Clinic'
        db.create_table(u'clinics_clinic', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=100)),
            ('slug', self.gf('django.db.models.fields.SlugField')(unique=True, max_length=50)),
            ('town', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('ward', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('lga', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=32, blank=True)),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rapidsms.Contact'], null=True, blank=True)),
            ('year_opened', self.gf('django.db.models.fields.CharField')(max_length=4, blank=True)),
            ('last_renovated', self.gf('django.db.models.fields.CharField')(max_length=4, blank=True)),
            ('lga_rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('pbf_rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'clinics', ['Clinic'])

        # Adding model 'ClinicStaff'
        db.create_table(u'clinics_clinicstaff', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('clinic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['clinics.Clinic'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, blank=True)),
            ('contact', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['rapidsms.Contact'], null=True, blank=True)),
            ('staff_type', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('year_started', self.gf('django.db.models.fields.CharField')(max_length=4, blank=True)),
            ('is_manager', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal(u'clinics', ['ClinicStaff'])

        # Adding model 'ClinicStatistic'
        db.create_table(u'clinics_clinicstatistic', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('clinic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['clinics.Clinic'])),
            ('month', self.gf('django.db.models.fields.DateField')()),
            ('statistic', self.gf('django.db.models.fields.CharField')(max_length=8)),
            ('float_value', self.gf('django.db.models.fields.FloatField')(null=True, blank=True)),
            ('int_value', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('text_value', self.gf('django.db.models.fields.CharField')(max_length=255, null=True, blank=True)),
            ('rank', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'clinics', ['ClinicStatistic'])

        # Adding unique constraint on 'ClinicStatistic', fields ['clinic', 'statistic', 'month']
        db.create_unique(u'clinics_clinicstatistic', ['clinic_id', 'statistic', 'month'])


    def backwards(self, orm):
        # Removing unique constraint on 'ClinicStatistic', fields ['clinic', 'statistic', 'month']
        db.delete_unique(u'clinics_clinicstatistic', ['clinic_id', 'statistic', 'month'])

        # Deleting model 'Clinic'
        db.delete_table(u'clinics_clinic')

        # Deleting model 'ClinicStaff'
        db.delete_table(u'clinics_clinicstaff')

        # Deleting model 'ClinicStatistic'
        db.delete_table(u'clinics_clinicstatistic')


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
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Contact']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_renovated': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'}),
            'lga': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'lga_rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'pbf_rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '50'}),
            'town': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'ward': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'year_opened': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'})
        },
        u'clinics.clinicstaff': {
            'Meta': {'object_name': 'ClinicStaff'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']"}),
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['rapidsms.Contact']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_manager': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'staff_type': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'year_started': ('django.db.models.fields.CharField', [], {'max_length': '4', 'blank': 'True'})
        },
        u'clinics.clinicstatistic': {
            'Meta': {'unique_together': "[('clinic', 'statistic', 'month')]", 'object_name': 'ClinicStatistic'},
            'clinic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['clinics.Clinic']"}),
            'float_value': ('django.db.models.fields.FloatField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'int_value': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'month': ('django.db.models.fields.DateField', [], {}),
            'rank': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'statistic': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'text_value': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'})
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
        }
    }

    complete_apps = ['clinics']