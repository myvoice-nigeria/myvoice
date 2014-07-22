from myvoice.settings.staging import *  # noqa


# There should be only minor differences from staging

DATABASES['default']['NAME'] = 'myvoice_local_vagrant'
DATABASES['default']['USER'] = 'myvoice_local_vagrant'

EMAIL_SUBJECT_PREFIX = '[Myvoice Local Vagrant] '

# Uncomment if using celery worker configuration
BROKER_URL = ('amqp://myvoice_local_vagrant:'
              '%(BROKER_PASSWORD)s@%(BROKER_HOST)s/myvoice_local_vagrant' % os.environ)
