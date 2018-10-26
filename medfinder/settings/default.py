"""
Django default settings for medfinder project.

Crate a local.py in this same folder to set your local settings.

"""

from os import path
from django.utils.translation import ugettext_lazy as _

import environ
import datetime

root = environ.Path(__file__) - 3
env = environ.Env(DEBUG=(bool, False), )
environ.Env.read_env(env_file=root('.env'))
BASE_DIR = root()

dirname = path.dirname

BASE_DIR = dirname(dirname(dirname(path.abspath(__file__))))
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', [])

SECRET_KEY = env('SECRET_KEY')

SITE_ID = env('SITE_ID')

LOCAL_APPS = (
    'auth_ex',
    'medfinder',
    'medications',
    'public',
    'epidemic',
    'historic',
    'vaccinefinder',
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.gis',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',

    'activity_log',
    'corsheaders',
    'django_celery_beat',
    'django_s3_storage',
    'localflavor',
    'phonenumber_field',
    'rest_registration',
    'rest_framework',
    'rest_framework_swagger',
) + LOCAL_APPS

AUTH_USER_MODEL = 'auth_ex.User'
LOGIN_REDIRECT_URL = '/admin/'

# --- STATIC FILES ---
STATIC_URL = '/static/'
STATIC_ROOT = env('STATIC_ROOT', default=(root - 1)('static'))

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# --- MEDIA ---
MEDIA_URL = '/media/'
MEDIA_ROOT = env('MEDIA_ROOT', default=(root - 1)('media'))

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': (
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
            )
        }
    },
]

MIDDLEWARE = (
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'activity_log.middleware.ActivityLogMiddleware',
)

ROOT_URLCONF = 'medfinder.urls'
WSGI_APPLICATION = 'medfinder.wsgi.application'

USE_TZ = True
TIME_ZONE = 'UTC'

# --- CORS RULES ---
CORS_ORIGIN_ALLOW_ALL = True

# --- ACTIVITY LOG ---

ACTIVITYLOG_METHODS = ('POST',)

NDC_DATABASE_URL = env('NDC_DATABASE_URL', default='')

CENSUS_API_KEY = env('CENSUS_API_KEY', default='')

GOOGLE_MAP_API_KEY = env('GOOGLE_MAP_API_KEY', default='')

# --- LANGUAGES ---
USE_I18N = True
USE_L10N = True
LANGUAGE_CODE = 'en-us'
# LANGUAGES = (
#     ('en', _('English')),
#     ('pl', _('Polish')),
# )
# LOCALE_PATHS = (
#     path.join(BASE_DIR, 'locale'),
# )

# --- FILE UPLOAD ---
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 * 1024 * 1024  # i.e. 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 * 1024 * 1024  # i.e. 100 MB
FILE_UPLOAD_PERMISSIONS = None
FILE_UPLOAD_DIRECTORY_PERMISSIONS = None

# --- DATABASE ---
# --- POSTGRESQL


DATABASES = {
    'default': env.db(
        default='postgis://postgres:postgres@postgres:5432/postgres'),
    'vaccinedb': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': env('VACCINEFINDER_HOST', default=''),
        'NAME': env('VACCINEFINDER_NAME', default=''),
        'PASSWORD': env('VACCINEFINDER_PASSWORD', default=''),
        'USER': env('VACCINEFINDER_USER', default=''),
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.9/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# --- S3 SETTINGS ---
S3_STORAGE_ENABLE = env.bool('S3_STORAGE_ENABLE', default=False)
if S3_STORAGE_ENABLE:
    DEFAULT_FILE_STORAGE = 'django_s3_storage.storage.S3Storage'
    STATICFILES_STORAGE = 'django_s3_storage.storage.StaticS3Storage'
    AWS_REGION = env('AWS_REGION')
    AWS_ACCESS_KEY_ID = env('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = env('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET_NAME = env('AWS_S3_BUCKET_NAME')
    AWS_S3_BUCKET_NAME_STATIC = env('AWS_S3_BUCKET_NAME_STATIC')
    AWS_S3_BUCKET_AUTH = env.bool('AWS_S3_BUCKET_AUTH', default=False)
    AWS_S3_MAX_AGE_SECONDS = 60 * 60 * 24 * 365  # 1 year.

# --- DJANGO COMPRESSOR ---
# STATICFILES_FINDERS += ('compressor.finders.CompressorFinder',)

# --- DJANGO REGISTRATION REDUX ---
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_AUTO_LOGIN = False

# --- CELERY ---
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/')

CELERYD_TASK_SOFT_TIME_LIMIT = 60 * 60 * 24

# --- CACHE ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "{}1".format(CELERY_BROKER_URL),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# CELERY_BEAT_SCHEDULE = {
#     'import_existing_medications': {
#         'task': 'medications.tasks.import_existing_medications',
#         'schedule': crontab(day_of_month=15),
#         'relative': True,
#     },
# }

# DEBUG TOOLBAR
ENABLE_DEBUG_TOOLBAR = env.bool(
    'DEBUG',
    default=False,
)

# --- DJANGO REST FRAMEWORK ---

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_jwt.authentication.JSONWebTokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    ),
}

# --- JWT ---

JWT_AUTH = {
    'JWT_EXPIRATION_DELTA': datetime.timedelta(days=1),
    'JWT_AUTH_HEADER_PREFIX': 'Token',
}

# --- REST REGISTRATION ---
FRONTEND_URL = env('FRONTEND_URL', default='localhost:3000')
REST_REGISTRATION = {
    'REGISTER_VERIFICATION_ENABLED': False,
    'REGISTER_EMAIL_VERIFICATION_ENABLED': False,

    'VERIFICATION_FROM_EMAIL': 'no-reply@example.com',

    'RESET_PASSWORD_VERIFICATION_URL':
    'https://{}/reset-password'.format(FRONTEND_URL),

    'USER_HIDDEN_FIELDS': (
        'is_active',
        'is_staff',
        'is_superuser',
        'user_permissions',
        'groups',
        'date_joined',
        'secret',
    ),
}


# EMAIL information
EMAIL_ENABLE = env.bool('EMAIL_ENABLE', default=True)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST = env('EMAIL_HOST', default='')
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
EMAIL_PORT = env('EMAIL_PORT', default=587)
EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)
FROM_EMAIL = env(
    'FROM_EMAIL',
    default='no-reply@example.com'
)
DEFAULT_FROM_EMAIL = env(
    'DEFAULT_FROM_EMAIL',
    default='webmaster@localhost',
)

if ENABLE_DEBUG_TOOLBAR:
    INSTALLED_APPS += (
        'debug_toolbar',
    )

    MIDDLEWARE += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    INTERNAL_IPS = ('172.18.0.1', '127.0.0.1', 'localhost')
    DEBUG_TOOLBAR_PANELS = [
        'debug_toolbar.panels.versions.VersionsPanel',
        'debug_toolbar.panels.timer.TimerPanel',
        'debug_toolbar.panels.settings.SettingsPanel',
        'debug_toolbar.panels.headers.HeadersPanel',
        'debug_toolbar.panels.request.RequestPanel',
        'debug_toolbar.panels.sql.SQLPanel',
        'debug_toolbar.panels.staticfiles.StaticFilesPanel',
        'debug_toolbar.panels.templates.TemplatesPanel',
        'debug_toolbar.panels.cache.CachePanel',
        'debug_toolbar.panels.signals.SignalsPanel',
        'debug_toolbar.panels.logging.LoggingPanel',
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ]
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'SHOW_TOOLBAR_CALLBACK': lambda *x: True,
    }

# ---PHONENUMBER FIELD ---

PHONENUMBER_DEFAULT_REGION = 'US'

DECIMAL_SEPARATOR = '.'

# --- STATES, COUNTIES & ZIPCODES ---
US_STATES_DATABASE = env(
    'US_STATES_DATABASE',
    default='https://raw.githubusercontent.com/PublicaMundi/MappingAPI/'
            'master/data/geojson/us-states.json',
)

# Use the {}_{} to format with the correspondent state code and name
US_ZIPCODES_DATABASE = env(
    'US_ZIPCODES_DATABASE',
    default='https://raw.githubusercontent.com/OpenDataDE/'
            'State-zip-code-GeoJSON/master/{}_{}_zip_codes_geo.min.json',
)

US_COUNTIES_DATABASE = env(
    'US_COUNTIES_DATABASE',
    default='http://eric.clst.org/assets/wiki/uploads/'
            'Stuff/gz_2010_us_050_00_500k.json',
)

GEOJSON_GEOGRAPHIC_CONTINENTAL_CENTER_US = {
    "type": "Point",
    "coordinates": [-98.579561, 39.828194],
}

ZOOM_US = 3
ZOOM_STATE = 7
ZOOM_ZIPCODE = 13

# --- SENTRY ---
RAVEN_DSN = env('RAVEN_DSN', default='')
if RAVEN_DSN:
    INSTALLED_APPS += ('raven.contrib.django.raven_compat', )
    RAVEN_CONFIG = {
        'dsn': RAVEN_DSN,
    }
    CELERYD_HIJACK_ROOT_LOGGER = False
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': True,
        'root': {
            'level': 'WARNING',
            'handlers': ['sentry'],
        },
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s '
                          '%(process)d %(thread)d %(message)s'
            },
        },
        'handlers': {
            'sentry': {
                # To capture more than ERROR, change to WARNING, INFO, etc.
                'level': 'INFO',
                'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',  # noqa
            },
            'console': {
                'level': 'DEBUG',
                'class': 'logging.StreamHandler',
                'formatter': 'verbose'
            }
        },
        'loggers': {
            'django.db.backends': {
                'level': 'ERROR',
                'handlers': ['console'],
                'propagate': False,
            },
            'raven': {
                'level': 'DEBUG',
                'handlers': ['console'],
                'propagate': False,
            },
            'sentry.errors': {
                'level': 'DEBUG',
                'handlers': ['console'],
                'propagate': False,
            },
            'celery': {
                'level': 'ERROR',
                'handlers': ['sentry', 'console'],
                'propagate': False,
            },
        },
    }
