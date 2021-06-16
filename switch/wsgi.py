#from gevent import monkey; monkey.patch_all(socket=True, dns=True, time=True, select=True,thread=False, os=True, ssl=True, httplib=False, aggressive=True)
#from psycogreen.gevent import patch_psycopg; patch_psycopg()


"""
WSGI config for switch project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os, sys

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "switch.settings"

#sys.path.append('/srv/applications/switch')

path = os.path.abspath(os.path.join(__file__, '..', '..'))
if path not in sys.path:
    sys.path.append(path)

os.environ["DJANGO_SETTINGS_MODULE"] = "switch.settings"

os.environ["CELERY_LOADER"] = "django"
# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.

from django.core.wsgi import get_wsgi_application
from switch.cassandra import cassandra_init


try:
	from uwsgidecorators import postfork
except ImportError:
	# We're not in a uWSGI context, no need to hook Cassandra session
	# initialization to the postfork event.
	pass
else:
	@postfork
	def _cassandra_init(**kwargs):
		cassandra_init(kwargs)


application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
#import djcelery

#djcelery.setup_loader()

from django.core.cache.backends.memcached import BaseMemcachedCache
BaseMemcachedCache.close = lambda self, **kwargs: None
