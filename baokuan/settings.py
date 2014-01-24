# Django settings for baokuan project.
from mongoengine import connect
import os

APP_NAME = 'baokuan'
ROOT_PATH = os.path.abspath(os.path.dirname(__file__))
env = os.getenv('ENV') or 'DEV'
ENV = env.upper()
HOST = 'luckytao.tk'

if ENV == 'DEV':
    DEBUG = True
    TEMPLATE_DEBUG = DEBUG
    MONGOHOST = '127.0.0.1'
    BAOKUAN_HOST = 'http://222.73.105.208/'
    SUB_DOMAIN = None

elif ENV == 'PRODUCTION':
    DEBUG = False
    TEMPLATE_DEBUG = DEBUG
    MONGOHOST = '127.0.0.1'
    BAOKUAN_HOST = 'http://222.73.105.208/'
    SUB_DOMAIN = 'http://{}/{}'.format(HOST, APP_NAME)

elif ENV == 'TEST':
    DEBUG = True
    TEMPLATE_DEBUG = DEBUG
    MONGOHOST = '127.0.0.1'
    BAOKUAN_HOST = 'http://222.73.105.208/'
    APP_NAME = 'baokuan_test'
    SUB_DOMAIN = None

connect(host=MONGOHOST, db=APP_NAME)
MONGOENGINE_USER_DOCUMENT = 'mongoengine.django.auth.User'
AUTHENTICATION_BACKENDS = (
    # 'mongoengine.django.auth.MongoEngineBackend',
    'apis.base.authentications.BaokuanEngineBackend',
)


ADMINS = (
    # ('Ethan', 'ethan@favbuy.com'),
)

MANAGERS = ADMINS

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    '*'
]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = ROOT_PATH

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/assets/' if DEBUG == True else '/baokuan/assets/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(STATIC_ROOT, 'static'),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'x0-@t%&#g55_hrx+226edxk_*$8vj5^-ok-aa(%fhd6lc_nr87'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'baokuan.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'baokuan.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ROOT_PATH, 'templates'),
    os.path.join(ROOT_PATH, 'templates', 'admins'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tastypie',
    'tastypie_mongoengine',
    'mongoengine.django.mongo_auth',
    'djcelery',
    'djcelery_email',
    'apis',
    'cron',
)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'
SESSION_ENGINE = 'mongoengine.django.sessions'

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'no-reply@favbuy.com'
EMAIL_HOST_PASSWORD = 'tempfavbuy88'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

CELERY_EMAIL_TASK_CONFIG = {
    'queue' : 'email',
    # 'rate_limit' : '50/m',
    'ignore_result': True,
}

from celery.schedules import crontab

BROKER_URL = 'redis://'

CELERYBEAT_SCHEDULE = {
    'score_rank': {
        'task': 'tasks.score_and_rank',
        'schedule': crontab(minute=0, hour=0)
    },
    'paper_online': {
        'task': 'tasks.score_and_rank',
        'schedule': crontab(minute=0, hour=0)
    },
    'lottery_online': {
        'task': 'tasks.score_and_rank',
        'schedule': crontab(minute=0, hour=0)
    },
    'notification': {
        'task': 'tasks.score_and_rank',
        'schedule': crontab(minute=0, hour=0)
    },
}
