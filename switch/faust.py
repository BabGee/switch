import os
import faust

from django.conf import settings

# make sure the gevent event loop is used as early as possible.
os.environ.setdefault('FAUST_LOOP', 'eventlet')

# set the default Django settings module for the 'faust' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'switch.settings')

#app = faust.App('switch', autodiscover=False, origin='switch')
from secondary.channels.notify import *

app = faust.App('switch')

@app.on_configured.connect
def configure_from_settings(app, conf, **kwargs):
    conf.broker = settings.FAUST_BROKER_URL
    conf.store = settings.FAUST_STORE_URL

'''
#app.discover(ignore=ignore_pattern)
def main():
	app.main()

if __name__ == '__main__':
	main()
	#app.discover(lambda: settings.INSTALLED_APPS)
'''
@app.discover
def discover(app):
	#app.discover()
	print('Request: {0!r}'.format(self.request))
#discover()
