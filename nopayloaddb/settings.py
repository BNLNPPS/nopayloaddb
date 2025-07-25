"""
Django settings for nopayloaddb project.

Generated by 'django-admin startproject' using Django 1.9.3.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'changetosomething'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework.authtoken',

    'cdb_rest'

#   'django_nose'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    #My middleware
    'nopayloaddb.middleware.RequestMiddleware',
]

ROOT_URLCONF = 'nopayloaddb.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
import socket

try:
    HOSTNAME = socket.gethostname()
except:
    HOSTNAME = 'localhost'

LOGPATH = os.environ.get("DJANGO_LOGPATH", default='/var/log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '{}/django-{}.log'.format(LOGPATH, HOSTNAME),
        },
        'console': {
            'class': 'logging.StreamHandler',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
if os.environ.get("DJANGO_DB_CONFIG") == "test_project":
    LOGGING['loggers']['django']['handlers'] = ['console']
    LOGGING['loggers']['django']['level'] = 'INFO'
    LOGGING['loggers']['django']['propagate'] = False


WSGI_APPLICATION = 'nopayloaddb.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.sqlite3',
#        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#    }
#}

#DATABASES = {
#    'default': {
#        'ENGINE': 'django.db.backends.postgresql_psycopg2',
#
#
#        'NAME':     os.environ.get("POSTGRES_DB",       default='dbname'),
#        'USER':     os.environ.get("POSTGRES_USER",     default='login'),
#        'PASSWORD': os.environ.get("POSTGRES_PASSWORD", default='password'),
#        'HOST':     os.environ.get("POSTGRES_HOST",     default='localhost'),
#        'PORT':     os.environ.get("POSTGRES_PORT",     default='5432'),
#
#    }
#}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',


        'NAME':     os.environ.get("POSTGRES_DB_W",       default='dbname'),
        'USER':     os.environ.get("POSTGRES_USER_W",     default='login'),
        'PASSWORD': os.environ.get("POSTGRES_PASSWORD_W", default='password'),
        'HOST':     os.environ.get("POSTGRES_HOST_W",     default='localhost'),
        'PORT':     os.environ.get("POSTGRES_PORT_W",     default='5432'),

        'CONN_MAX_AGE': 60,  # Close and reopen every 1m
    },
    'read_db_1': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',


        'NAME':     os.environ.get("POSTGRES_DB_R1",       default='dbname'),
        'USER':     os.environ.get("POSTGRES_USER_R1",     default='login'),
        'PASSWORD': os.environ.get("POSTGRES_PASSWORD_R1", default='password'),
        'HOST':     os.environ.get("POSTGRES_HOST_R1",     default='localhost'),
        'PORT':     os.environ.get("POSTGRES_PORT_R1",     default='5432'),

        'CONN_MAX_AGE': 60,  # Close and reopen every 1m
    },
    'read_db_2': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',


        'NAME':     os.environ.get("POSTGRES_DB_R2",       default='dbname'),
        'USER':     os.environ.get("POSTGRES_USER_R2",     default='login'),
        'PASSWORD': os.environ.get("POSTGRES_PASSWORD_R2", default='password'),
        'HOST':     os.environ.get("POSTGRES_HOST_R2",     default='localhost'),
        'PORT':     os.environ.get("POSTGRES_PORT_R2",     default='5432'),

        'CONN_MAX_AGE': 60,  # Close and reopen every 1m
    },
}

# Read database configurations
if os.environ.get("DJANGO_DB_CONFIG") == "test_project":
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ.get("POSTGRES_DB", "dbname_project1"),
        'USER': os.environ.get("POSTGRES_USER", "user_project1"),
        'PASSWORD': os.environ.get("POSTGRES_PASSWORD", "password_project1"),
        'HOST': os.environ.get("POSTGRES_HOST", "localhost"),
        'PORT': os.environ.get("POSTGRES_PORT", "5432"),

        'CONN_MAX_AGE': 60,  # Close and reopen every 1m
    }


DATABASE_ROUTERS = ['nopayloaddb.db_router.ReadWriteRouter']

REST_FRAMEWORK = {
#    'DEFAULT_AUTHENTICATION_CLASSES': (
#        'rest_framework.authentication.TokenAuthentication',
#    ),
    #'DEFAULT_AUTHENTICATION_CLASSES': (
    #    'cdb_rest.authentication.CustomJWTAuthentication',
    #),
    #'DEFAULT_PERMISSION_CLASSES': (
    #    'rest_framework.permissions.IsAuthenticated',
    #),

    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
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

SIMPLE_JWT = {
    #'SIGNING_KEY': settings.SECRET_KEY,
    #ZZ'VERIFYING_KEY':SECRET_KEY,
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'AUTH_HEADER_TYPES': ('JWT', 'Bearer'),
    'USER_ID_CLAIM': 'user_id',

    #'JTI_CLAIM': 'jti',
}



# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

#USE_TZ = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATIC_URL = '/static/'

# Use nose to run all tests
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'

# Tell nose to measure coverage on the 'foo' and 'bar' apps
NOSE_ARGS = [
    '--with-coverage',
    '--cover-package=cdb_rest',
]
