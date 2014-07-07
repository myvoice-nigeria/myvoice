from myvoice.settings.base import *  # noqa


os.environ.setdefault('CACHE_HOST', '127.0.0.1:11211')
os.environ.setdefault('BROKER_HOST', '127.0.0.1:5672')

DEBUG = False
TEMPLATE_DEBUG = DEBUG

DATABASES['default']['NAME'] = 'myvoice_staging'
DATABASES['default']['USER'] = 'myvoice_staging'
DATABASES['default']['HOST'] = os.environ.get('DB_HOST', '')
DATABASES['default']['PORT'] = os.environ.get('DB_PORT', '')
DATABASES['default']['PASSWORD'] = os.environ['DB_PASSWORD']

PUBLIC_ROOT = '/var/www/myvoice/public/'

STATIC_ROOT = os.path.join(PUBLIC_ROOT, 'static')

MEDIA_ROOT = os.path.join(PUBLIC_ROOT, 'media')

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '%(CACHE_HOST)s' % os.environ,
    }
}

EMAIL_SUBJECT_PREFIX = '[Myvoice Staging] '
EMAIL_HOST = 'smtp.sendgrid.net'
EMAIL_HOST_USER = 'reboot-myvoice'
EMAIL_HOST_PASSWORD = os.environ['SENDGRID_PASSWORD']
EMAIL_PORT = 587
EMAIL_USE_TLS = True

COMPRESS_ENABLED = True

SESSION_COOKIE_SECURE = False  # FIXME - re-enable SSL on staging

SESSION_COOKIE_HTTPONLY = True

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(';')

# Uncomment if using celery worker configuration
BROKER_URL = ('amqp://myvoice_staging:'
              '%(BROKER_PASSWORD)s@%(BROKER_HOST)s/myvoice_staging' % os.environ)

LOGGING['handlers']['file']['filename'] = '/var/www/myvoice/log/myvoice.log'
