from myvoice.settings.staging import *

# There should be only minor differences from staging

DATABASES['default']['NAME'] = 'myvoice_production'
DATABASES['default']['USER'] = 'myvoice_production'

EMAIL_SUBJECT_PREFIX = '[Myvoice Prod] '

# Uncomment if using celery worker configuration
# BROKER_URL = 'amqp://myvoice_production:%(BROKER_PASSWORD)s@%(BROKER_HOST)s/myvoice_production' % os.environ