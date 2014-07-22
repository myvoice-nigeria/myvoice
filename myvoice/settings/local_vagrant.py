from myvoice.settings.staging import *  # noqa


# There should be only minor differences from staging

DATABASES['default']['NAME'] = 'myvoice_local'
DATABASES['default']['USER'] = 'myvoice_local'

EMAIL_SUBJECT_PREFIX = '[Myvoice Local] '

# Uncomment if using celery worker configuration
BROKER_URL = ('amqp://myvoice_local:'
              '%(BROKER_PASSWORD)s@%(BROKER_HOST)s/myvoice_local' % os.environ)
