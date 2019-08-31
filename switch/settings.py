import os
import datetime
import psycopg2

# Django settings for switch project.
#from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

#import ConfigParser
import configparser

#cf = ConfigParser.ConfigParser()

cf = configparser.ConfigParser()
cf.read(os.path.join(BASE_DIR, 'switch/conf/switch.properties'))
logroot =  os.getenv("LOG_root", cf.get('LOG','root')).strip()

#print cf._sections

#faust
FAUST_BROKER_URL = 'kafka://localhost:9092'
FAUST_STORE_URL = 'rocksdb://'

try:conf_products = os.getenv("INSTALLED_APPS_products", cf.get('INSTALLED_APPS','products'))
except:conf_products=''
products=conf_products.split(",")

try:conf_thirdparty =  os.getenv("INSTALLED_APPS_thirdparty", cf.get('INSTALLED_APPS','thirdparty'))
except:conf_thirdparty = ''
thirdparty=conf_thirdparty.split(",")

dbengine =  os.getenv("DATABASES_default_dbengine", cf.get('DATABASES','default_dbengine'))
dbname =  os.getenv("DATABASES_default_dbname", cf.get('DATABASES','default_dbname'))
dbuser =  os.getenv("DATABASES_default_dbuser", cf.get('DATABASES','default_dbuser'))
dbpassword =  os.getenv("DATABASES_default_dbpassword", cf.get('DATABASES','default_dbpassword'))
dbhost =  os.getenv("DATABASES_default_dbhost", cf.get('DATABASES','default_dbhost'))
dbport =  os.getenv("DATABASES_default_dbport", cf.get('DATABASES','default_dbport'))
                                   
smtphost =  os.getenv("SMTP_default_host", cf.get('SMTP','default_host'))
smtpport =  os.getenv("SMTP_default_port", cf.get('SMTP','default_port'))
smtptls_default =  os.getenv("SMTP_tls", cf.get('SMTP','tls'))
tls_default = {'True': True, 'False': False}
smtptls = tls_default[smtptls_default]
                                     
conf_hosts =  os.getenv("ALLOWED_HOSTS_hosts", cf.get('ALLOWED_HOSTS','hosts'))
hosts = conf_hosts.split(",")        
    
installed_apps = products+thirdparty
installed_apps = filter(None, installed_apps)

primary = (
    'primary.core.administration',
    'primary.core.api',
    'primary.core.upc',
    'primary.core.bridge',
	)

secondary = (
    'secondary.channels.vcs',
    'secondary.channels.iic',
    'secondary.channels.dsc',
    'secondary.channels.notify',
    'secondary.erp.pos',
    'secondary.erp.ads',
    'secondary.erp.crm',
    'secondary.erp.survey',
    'secondary.erp.loyalty',
    'secondary.finance.vbs',
    'secondary.finance.crc',
    'secondary.finance.paygate',
	)

installed_apps = primary + secondary + tuple(installed_apps)


timezone='Africa/Nairobi'
DEBUG = False
#TEMPLATE_DEBUG = DEBUG #Deprecated 1.8

GEOIP_PATH = '/usr/share/GeoIP'

#EMAIL_HOST = 'smtp.gmail.com'
#EMAIL_HOST_USER = 'interintel.helpdesk@gmail.com'
#EMAIL_HOST_PASSWORD = 'User@InterIntel1234'
#EMAIL_PORT = 587
#EMAIL_USE_TLS = True

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = smtphost
#EMAIL_PORT = 25
EMAIL_PORT = smtpport
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_USE_TLS = smtptls
#EMAIL_USE_SSL = True
DEFAULT_FROM_EMAIL = 'InterIntel <noreply@interintel.co.ke>'

GRAPH_MODELS = {
  'all_applications': True,
  'group_models': True,
}

ADMINS = (
     ('InterIntel Support', 'support@interintel.co.ke'),
)

SUIT_CONFIG = {
    'ADMIN_NAME': 'Switch Administrator',


}

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': dbengine, # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': dbname,                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': dbuser,
        'PASSWORD': dbpassword,
        'HOST': dbhost,                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': dbport,                      # Set to empty string for default.
	'CONN_MAX_AGE': 600,
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = hosts

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Africa/Nairobi'
#TIME_ZONE = 'UTC'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media').replace('\\','/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
#STATIC_ROOT = ''
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static').replace('\\','/')

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
#STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
#)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'hj-99b$$ap_z4zmd=0z$ol5691_xe+$xn!n5horl*jfymibrrc'

ROOT_URLCONF = 'switch.urls'

WSGI_APPLICATION = 'switch.wsgi.application'


'''
INSTALLED_APPS = (
    'suit',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django_extensions',
    'django_celery_results',
    'django_celery_beat',
    'primary.core.administration',
    'primary.core.api',
    'primary.core.upc',
    'primary.core.bridge',
)
'''
INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.gis',
    'django_extensions',
    'django_celery_beat',
) +  installed_apps

'''

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)


'''
MIDDLEWARE = [
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

'''
#REQUEST CONTEXT PROCESSOR
TEMPLATE_CONTEXT_PROCESSORS += (
    'django.core.context_processors.request',
)
'''
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.

LOGFILE='info.log'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s-%(name)s %(module)s %(process)d %(thread)d-(%(threadName)-2s) %(levelname)s-%(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'special': {
            '()': 'django.utils.log.RequireDebugFalse',
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['special']
        },
        
    },

    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },

    }
}

if logroot not in [None,""]:
	LOGGING['handlers']['file_actions'] = {                # define and name a handler
            'level': 'DEBUG',
            'class': 'logging.FileHandler', # set the logging class to log to a file
            #'class': 'logging.handlers.QueueHandler', # set the logging class to log to a file
            'formatter': 'verbose',         # define the formatter to associate
            'filename': os.path.join(logroot, '', LOGFILE) # log file
        }
	LOGGING['loggers']['logview.usersaves']: {               # define another logger
            'handlers': ['file_actions'],  # associate a different handler
            'level': 'INFO',                 # specify the logging level
            'propagate': True,
        } 

	for app in installed_apps:
		LOGGING['handlers'][app] = {
	            'level' : 'INFO',
        	    'formatter' : 'verbose', # from the django doc example
	            'class' : 'logging.handlers.TimedRotatingFileHandler',
	            #'class' : 'logging.handlers.QueueHandler',
        	    'filename' : os.path.join(logroot, '', app+'.log'), # full path works
	            'when' : 'midnight',
	            'interval' : 1,
		    'backupCount': 5,
	        }

		LOGGING['loggers'][app] = {
	            'handlers': [app],
	            'level': 'INFO',
	        }

else:
	LOGGING['file_actions'] = {
            'level':'INFO',
            'class':'logging.StreamHandler',
            'formatter': 'verbose',
        }
	LOGGING['loggers']['logview.usersaves']: {               # define another logger
            'handlers': ['file_actions'],  # associate a different handler
            'level': 'INFO',                 # specify the logging level
            'propagate': True,
        } 

	for app in installed_apps:
		LOGGING['handlers'][app] = {
	            'level':'INFO',
        	    'class':'logging.StreamHandler',
	            'formatter': 'verbose',
	        }

		LOGGING['loggers'][app] = {
	            'handlers': [app],
	            'level': 'INFO',
	        }



