import os
import faust

import django
from django.conf import settings
from django.utils.module_loading import import_module

# make sure the gevent event loop is used as early as possible.
os.environ.setdefault('FAUST_LOOP', 'eventlet')

# set the default Django settings module for the 'faust' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'switch.settings')

# set for models to run on async
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"


#app = faust.App('django-switch', autodiscover=False, origin='faustapp')
app = faust.App('switch-faust')

@app.on_configured.connect
def configure_from_settings(app, conf, **kwargs):
    conf.broker = settings.FAUST_BROKER_URL
    conf.store = settings.FAUST_STORE_URL

#Apps Require Loading for Discovery
django.setup()

##Discover agents modules only
#module_name = 'agents'
#
##app.discover('secondary.channels.notify')
#def autodiscover(django_apps):
#	for django_app in django_apps:
#		# Attempt to import the app's ``module_name``.
#		try:
#			import_module('{0}.{1}'.format(django_app, module_name))
#			print('found: %s' % django_app)
#		except Exception as e:
#			print('%s: :%s' % (e,django_app))
#			pass
#
#autodiscover(settings.INSTALLED_APPS)
#
'''
def main():
    app.main()
if __name__ == '__main__':
    main()
'''

