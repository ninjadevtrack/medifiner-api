"""
Django default settings for medfinder project.

Crate a local.py in this same folder to set your local settings.

"""

from os import path
from django.utils.translation import ugettext_lazy as _

import environ

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
    'medications'
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
    'localflavor',
    'phonenumber_field',
    'rest_registration',
    'rest_framework',
    'rest_framework.authtoken',
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
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # i.e. 2.5 MB
FILE_UPLOAD_PERMISSIONS = None
FILE_UPLOAD_DIRECTORY_PERMISSIONS = None

# --- DATABASE ---
# --- POSTGRESQL
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': 'postgres',
        'HOST': 'postgres',
        'PORT': '5432',
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


# --- DJANGO COMPRESSOR ---
# STATICFILES_FINDERS += ('compressor.finders.CompressorFinder',)

# --- CACHE ---
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/1",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}
# --- DJANGO REGISTRATION REDUX ---
ACCOUNT_ACTIVATION_DAYS = 7
REGISTRATION_AUTO_LOGIN = False

# --- CELERY ---
CELERY_BROKER_URL = env('CELERY_BROKER_URL', default='redis://redis:6379/')

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
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.AllowAny',
    )
}

# --- REST REGISTRATION ---
FRONTEND_URL = env('FRONTEND_URL', default='localhost:8000')
REST_REGISTRATION = {
    'REGISTER_VERIFICATION_ENABLED': True,

    'RESET_PASSWORD_VERIFICATION_URL': '/reset-password/',

    'REGISTER_EMAIL_VERIFICATION_ENABLED': True,

    'VERIFICATION_FROM_EMAIL': 'no-reply@example.com',

    'REGISTER_VERIFICATION_URL':
    'https://{}/verify-user/'.format(FRONTEND_URL),

    'RESET_PASSWORD_VERIFICATION_URL':
    'https://{}/reset-password/'.format(FRONTEND_URL),

    'REGISTER_EMAIL_VERIFICATION_URL':
    'https://{}/verify-email/'.format(FRONTEND_URL),
}

EMAIL_BACKEND = env(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
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
        },
    }
